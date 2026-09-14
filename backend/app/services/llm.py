import json
from pathlib import Path

import httpx

from app.config import settings

_KB_PATH = Path(__file__).parent.parent / "data" / "knowledge_base.json"
_knowledge_base = json.loads(_KB_PATH.read_text(encoding="utf-8"))

BASE_SYSTEM_PROMPT = f"""คุณคือ AI ผู้ช่วยประจำตู้คีออสก์ (kiosk) ของสาขาวิชาวิทยาการคอมพิวเตอร์ มหาวิทยาลัยแม่โจ้
ตอบคำถามเกี่ยวกับข้อมูลสาขา อาคาร สถานที่ และข่าวสารของภาควิชา โดยใช้ข้อมูลอ้างอิงต่อไปนี้:

{json.dumps(_knowledge_base, ensure_ascii=False, indent=2)}

หากคำถามอยู่นอกเหนือข้อมูลที่มี ให้ตอบอย่างสุภาพว่าไม่มีข้อมูลนี้ และแนะนำให้ติดต่อเจ้าหน้าที่สาขาโดยตรง
ตอบสั้น กระชับ เป็นภาษาไทย เว้นแต่ผู้ถามใช้ภาษาอังกฤษ"""


def build_system_prompt(student_context: str | None = None) -> str:
    """Append the caller's own schedule/exam data (already scoped to that
    one card_uid by the caller -- see routers/chatbot.py) so the assistant
    can answer "ตารางเรียนของฉันวันนี้มีอะไรบ้าง" style questions instead of
    only the static department FAQ."""
    if not student_context:
        return BASE_SYSTEM_PROMPT
    return f"{BASE_SYSTEM_PROMPT}\n\nข้อมูลตารางเรียน/ตารางสอบของผู้ถามคนนี้โดยเฉพาะ:\n{student_context}"


class LLMError(RuntimeError):
    pass


def _ask_claude(message: str, system_prompt: str) -> str:
    if not settings.anthropic_api_key:
        raise LLMError("ANTHROPIC_API_KEY is not configured")
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _ask_ollama(message: str, system_prompt: str) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        "stream": False,
    }
    resp = httpx.post(f"{settings.ollama_base_url}/api/chat", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _ask_gemini(message: str, system_prompt: str) -> str:
    if not settings.gemini_api_key:
        raise LLMError("GEMINI_API_KEY is not configured")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
    }
    resp = httpx.post(
        url,
        params={"key": settings.gemini_api_key},
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise LLMError(f"Gemini API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected Gemini response shape: {data}") from exc


def ask(message: str, student_context: str | None = None) -> str:
    system_prompt = build_system_prompt(student_context)
    if settings.llm_provider == "ollama":
        return _ask_ollama(message, system_prompt)
    if settings.llm_provider == "gemini":
        return _ask_gemini(message, system_prompt)
    return _ask_claude(message, system_prompt)
