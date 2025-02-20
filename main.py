import logging
import os
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BaseSettings, Field
from dotenv import load_dotenv
import httpx
import uvicorn
from enum import Enum

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    telex_channel_id: str = Field(..., env='TELEX_CHANNEL_ID')
    telex_base_url: str = Field('https://ping.telex.im/v1/webhooks', env='TELEX_BASE_URL')
    
    class Config:
        env_file = '.env'

class TicketPriority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

class TicketStatus(str, Enum):
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    SOLVED = "solved"
    CLOSED = "closed"

class Requester(BaseModel):
    email: str
    name: Optional[str] = None

class Ticket(BaseModel):
    id: int
    subject: str
    status: TicketStatus
    priority: Optional[TicketPriority] = None
    requester: Requester

class ZendeskWebhook(BaseModel):
    ticket: Ticket

class TelexMessage(BaseModel):
    channel: str
    event: str = "message"
    data: Dict[str, Any]

class WebhookService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.telex_webhook_url = f"{settings.telex_base_url}/{settings.telex_channel_id}"

    def format_telex_message(self, ticket: Ticket) -> TelexMessage:
        """Formats a Zendesk ticket update as a Telex message."""
        priority_emoji = {
            TicketPriority.URGENT: "🔴",
            TicketPriority.HIGH: "🟠",
            TicketPriority.NORMAL: "🟡",
            TicketPriority.LOW: "🟢"
        }
        
        status_emoji = {
            TicketStatus.NEW: "🆕",
            TicketStatus.OPEN: "📖",
            TicketStatus.PENDING: "⏳",
            TicketStatus.SOLVED: "✅",
            TicketStatus.CLOSED: "🔒"
        }

        priority_display = f"{priority_emoji.get(ticket.priority, '⚪')} {ticket.priority.value.title()}" if ticket.priority else "Not set"
        
        return TelexMessage(
            channel=self.settings.telex_channel_id,
            data={
                "text": (
                    f"🎫 **Ticket #{ticket.id} Updated!**\n"
                    f"📌 **Subject:** {ticket.subject}\n"
                    f"{status_emoji.get(ticket.status, '🔘')} **Status:** {ticket.status.value.title()}\n"
                    f"⚡ **Priority:** {priority_display}\n"
                    f"👤 **Requester:** {ticket.requester.email}"
                )
            }
        )

    async def send_to_telex(self, message: TelexMessage) -> None:
        """Sends a message to Telex with retry logic."""
        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    response = await client.post(
                        self.telex_webhook_url,
                        json=message.dict(),
                        headers={"Content-Type": "application/json"},
                        timeout=10.0
                    )
                    response.raise_for_status()
                    return
                except httpx.TimeoutException:
                    if attempt == 2:
                        raise HTTPException(status_code=504, detail="Telex service timeout")
                    await asyncio.sleep(1 * (attempt + 1))
                except httpx.HTTPError as e:
                    if attempt == 2:
                        raise HTTPException(status_code=502, detail=f"Telex service error: {str(e)}")
                    await asyncio.sleep(1 * (attempt + 1))

# Initialize FastAPI and dependencies
app = FastAPI(title="Zendesk to Telex Integration")
settings = Settings()
webhook_service = WebhookService(settings)

# Configure logging and CORS
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.post("/zendesk-integration")
async def zendesk_integration(webhook_data: ZendeskWebhook) -> JSONResponse:
    """Handles incoming Zendesk webhooks and forwards them to Telex."""
    try:
        # Format and send message to Telex
        telex_message = webhook_service.format_telex_message(webhook_data.ticket)
        await webhook_service.send_to_telex(telex_message)

        return JSONResponse(
            content={"status": "success", "message": "Notification sent to Telex"},
            status_code=200
        )

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
