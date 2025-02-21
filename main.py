import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],  
    allow_headers=["*"],
)

# Retrieve Telex webhook details
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request) -> JSONResponse:
    try:
        # Parse JSON data
        data = await request.json()
        ticket = data.get("ticket", {})

        # Validate required fields
        if not ticket:
            return JSONResponse(content={"error": "Missing 'ticket' data in request."}, status_code=400)

        # Extract ticket details
        ticket_id = str(ticket.get("id", "Unknown"))
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")

        # Construct payload for Telex
        telex_payload = {
            "event_name": "Zendesk Ticket Update",
            "username": "ZendeskBot",
            "status": "success",
            "message": f"\U0001F3AB **Ticket #{ticket_id} Updated!**\n"
                        f"\U0001F4CC **Subject:** {subject}\n"
                        f"\U0001F518 **Status:** {status}\n"
                        f"⚡ **Priority:** {priority}\n"
                        f"\U0001F464 **Requester:** {requester_email}"
        }

        # Send to Telex.im
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TELEX_WEBHOOK_URL,
                json=telex_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                follow_redirects=True
            )
            response.raise_for_status()
            return JSONResponse(content={"message": "Sent to Telex"}, status_code=200)

    except httpx.RequestError:
        return JSONResponse(content={"error": "Failed to send request to Telex"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
