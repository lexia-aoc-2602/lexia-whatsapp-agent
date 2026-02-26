#!/usr/bin/env python3
"""
Lexia WhatsApp Agent - Agent Development Kit (ADK) Integration
Integrates Google's ADK with WhatsApp Business API and Meta webhooks
"""

import os
import json
import logging
from typing import Any
from fastapi import FastAPI, Request, HTTPException
from google.adk.agents import Agent
from google.adk.runners import FastAPIRunner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables for Meta WhatsApp API
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "551528574703551")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "lexia-aoc-2602")
WABA_ID = os.getenv("WABA_ID", "535733579621373")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://graph.facebook.com/v21.0/551528574703551/messages")

# Initialize FastAPI app
app = FastAPI(title="Lexia WhatsApp Agent", version="1.0.0")

# Create the ADK Agent for WhatsApp
def create_whatsapp_agent() -> Agent:
    """Create a WhatsApp-enabled agent using Google ADK"""
    
    agent = Agent(
        name="lexia_whatsapp_agent",
        model="gemini-2.5-flash",
        instruction="""Você é Léxia, um assistente de IA amigável e eficiente.
        
Sua missão é:
- Responder perguntas dos usuários de forma clara e concisa
- Fornecer informações úteis e precisas
- Manter um tom profissional mas amigável
- Oferecer ajuda adicional quando necessário

Sempre responda em português brasileiro, a menos que o usuário use outro idioma.""",
        description="Assistente de IA para WhatsApp Business",
    )
    
    return agent

# Initialize the agent
whatsapp_agent = create_whatsapp_agent()

# Create FastAPI runner for ADK
runner = FastAPIRunner(agent=whatsapp_agent, app=app)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Lexia WhatsApp Agent",
        "version": "1.0.0"
    }

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Webhook verification endpoint for Meta WhatsApp Business API
    Meta sends a GET request to verify the webhook
    """
    try:
        verify_token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        if verify_token != VERIFY_TOKEN:
            logger.warning(f"Invalid verify token received: {verify_token}")
            raise HTTPException(status_code=403, detail="Invalid verify token")
        
        logger.info("Webhook verified successfully")
        return int(challenge)
    
    except Exception as e:
        logger.error(f"Webhook verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook verification failed")

@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming messages from WhatsApp Business API
    """
    try:
        body = await request.json()
        logger.info(f"Received webhook payload: {json.dumps(body, indent=2)}")
        
        # Check if this is a message event
        if body.get("object") != "whatsapp_business_account":
            logger.warning(f"Unexpected object type: {body.get('object')}")
            return {"status": "ok"}
        
        # Extract message details
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            logger.info("No messages in webhook payload")
            return {"status": "ok"}
        
        # Process each message
        for message in messages:
            await process_whatsapp_message(message, value)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_whatsapp_message(message: dict, context: dict):
    """
    Process incoming WhatsApp message and send response through agent
    """
    try:
        from_number = message.get("from")
        message_id = message.get("id")
        message_type = message.get("type", "text")
        
        logger.info(f"Processing message {message_id} from {from_number} (type: {message_type})")
        
        # Extract message text
        user_message = ""
        if message_type == "text":
            user_message = message.get("text", {}).get("body", "")
        elif message_type == "interactive":
            # Handle interactive messages (buttons, lists, etc.)
            interactive = message.get("interactive", {})
            if "button_reply" in interactive:
                user_message = interactive["button_reply"].get("title", "")
            elif "list_reply" in interactive:
                user_message = interactive["list_reply"].get("title", "")
        
        if not user_message:
            logger.warning(f"No text content in message {message_id}")
            return
        
        # Process message through ADK agent
        logger.info(f"Sending to agent: {user_message}")
        response = await whatsapp_agent.generate_content(user_message)
        
        # Send response back to WhatsApp
        await send_whatsapp_message(from_number, response)
        
        # Mark message as read
        await mark_message_as_read(message_id)
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)

async def send_whatsapp_message(to_number: str, message_text: str):
    """
    Send message to WhatsApp user via Meta API
    """
    try:
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message_text
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URL,
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to send message: {response.status}")
                    logger.error(await response.text())
                else:
                    logger.info(f"Message sent successfully to {to_number}")
    
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}", exc_info=True)

async def mark_message_as_read(message_id: str):
    """
    Mark message as read in WhatsApp
    """
    try:
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages",
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to mark message as read: {response.status}")
                else:
                    logger.info(f"Message {message_id} marked as read")
    
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}", exc_info=True)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Lexia WhatsApp Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook",
            "adk_ui": "/adk"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    
    logger.info(f"Starting Lexia WhatsApp Agent on port {port}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    logger.info(f"Phone Number ID: {PHONE_NUMBER_ID}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
