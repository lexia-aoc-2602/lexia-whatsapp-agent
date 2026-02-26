#!/usr/bin/env python3
"""
Lexia WhatsApp Agent v2.0
Integra Google Gemini com WhatsApp Business API via Meta Cloud API
"""

import os
import json
import logging
import httpx
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Configurações Meta / WhatsApp ───────────────────────────────────────────
PHONE_NUMBER_ID       = os.getenv("PHONE_NUMBER_ID", "978917245310761")
VERIFY_TOKEN          = os.getenv("VERIFY_TOKEN", "lexia-aoc-2602")
WABA_ID               = os.getenv("WABA_ID", "2793719140803043")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
META_API_VERSION      = os.getenv("META_API_VERSION", "v21.0")

# ─── Configurações IA ────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.manus.im/api/llm-proxy/v1")
AI_MODEL        = os.getenv("AI_MODEL", "gemini-2.5-flash")

# ─── Instruções do agente ────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é Léxia, assistente de IA da Léxia Locadora de Veículos.

Sua missão:
- Atender clientes com simpatia e profissionalismo
- Responder dúvidas sobre locação de veículos, preços, disponibilidade e reservas
- Fornecer informações claras e objetivas
- Encaminhar para um atendente humano quando necessário

Responda sempre em português brasileiro, de forma concisa (máximo 3 parágrafos).
Nunca invente informações sobre preços ou disponibilidade — diga que vai verificar."""

app = FastAPI(title="Lexia WhatsApp Agent", version="2.0.0")


async def call_ai(user_message: str, user_name: str = "") -> str:
    """Chama o modelo de IA e retorna a resposta."""
    try:
        system = SYSTEM_PROMPT
        if user_name:
            system += f"\n\nO cliente se chama {user_name}."

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user_message},
            ],
            "max_tokens": 500,
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Erro ao chamar IA: {e}", exc_info=True)
        return "Olá! Sou a Léxia, assistente da Léxia Locadora. No momento estou com dificuldades técnicas. Por favor, tente novamente em instantes."


async def send_whatsapp_message(to_number: str, text: str) -> bool:
    """Envia mensagem de texto via Meta Cloud API."""
    if not WHATSAPP_ACCESS_TOKEN:
        logger.error("WHATSAPP_ACCESS_TOKEN não configurado!")
        return False

    url = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                logger.info(f"Mensagem enviada para {to_number}")
                return True
            else:
                logger.error(f"Falha ao enviar: {resp.status_code} — {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
        return False


async def mark_as_read(message_id: str):
    """Marca mensagem como lida."""
    if not WHATSAPP_ACCESS_TOKEN:
        return
    url = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, headers=headers, json=payload)
    except Exception as e:
        logger.warning(f"Não foi possível marcar como lida: {e}")


async def process_message(message: dict, contact: dict):
    """Processa uma mensagem recebida e envia resposta."""
    from_number = message.get("from", "")
    message_id  = message.get("id", "")
    msg_type    = message.get("type", "text")
    user_name   = contact.get("profile", {}).get("name", "")

    user_text = ""
    if msg_type == "text":
        user_text = message.get("text", {}).get("body", "")
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        user_text = (
            interactive.get("button_reply", {}).get("title")
            or interactive.get("list_reply", {}).get("title")
            or ""
        )
    elif msg_type == "audio":
        user_text = "O cliente enviou um áudio."
    elif msg_type == "image":
        caption = message.get("image", {}).get("caption", "")
        user_text = f"O cliente enviou uma imagem. Legenda: {caption}" if caption else "O cliente enviou uma imagem."
    elif msg_type == "document":
        user_text = "O cliente enviou um documento."
    elif msg_type == "location":
        loc = message.get("location", {})
        user_text = f"O cliente compartilhou localização: lat={loc.get('latitude')}, lon={loc.get('longitude')}"
    else:
        user_text = f"O cliente enviou mensagem do tipo '{msg_type}'."

    if not user_text:
        logger.warning(f"Mensagem sem conteúdo de {from_number}")
        return

    logger.info(f"[{from_number}] {user_name}: {user_text}")

    await mark_as_read(message_id)

    response_text = await call_ai(user_text, user_name)
    logger.info(f"[{from_number}] Resposta: {response_text[:80]}...")

    await send_whatsapp_message(from_number, response_text)


@app.get("/")
async def root():
    return {
        "service": "Lexia WhatsApp Agent",
        "version": "2.0.0",
        "status": "running",
        "ai_available": bool(OPENAI_API_KEY),
        "model": AI_MODEL,
        "phone_number_id": PHONE_NUMBER_ID,
        "token_configured": bool(WHATSAPP_ACCESS_TOKEN),
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Lexia WhatsApp Agent",
        "version": "2.0.0",
        "ai_available": bool(OPENAI_API_KEY),
        "token_configured": bool(WHATSAPP_ACCESS_TOKEN),
    }


@app.get("/webhook")
async def verify_webhook(request: Request):
    mode      = request.query_params.get("hub.mode")
    token     = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verificado!")
        return PlainTextResponse(content=challenge)

    raise HTTPException(status_code=403, detail="Verificação falhou")


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        logger.info(f"Webhook: {json.dumps(body)[:300]}")

        if body.get("object") != "whatsapp_business_account":
            return {"status": "ok"}

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value    = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [{}])

                for i, message in enumerate(messages):
                    contact = contacts[i] if i < len(contacts) else {}
                    background_tasks.add_task(process_message, message, contact)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Erro no webhook: {e}", exc_info=True)
        return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Iniciando Lexia WhatsApp Agent na porta {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
