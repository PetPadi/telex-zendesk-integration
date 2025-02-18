import httpx
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

# Telex Webhook Details
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration/")
async def zendesk_integration(request: Request):
    try:
        data = await request.json()
        ticket = data.get("ticket", {})

        # Extract required ticket details
        ticket_id = ticket.get("id", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")
        subject = ticket.get("subject", "No Subject")
        requester = ticket.get("requester", {})
        requester_name = requester.get("name", "Unknown")
        requester_email = requester.get("email", "Unknown")

        telex_payload = {
            "channel": TELEX_CHANNEL_ID,
            "event": "message",
            "data": {
                "text": (
                    f"Ticket #{ticket_id} Updated!\n"
                    f"Subject: {subject}\n"
                    f"Status: {status}\n"
                    f"Priority: {priority}\n"
                    f"Opened by: {requester_name} ({requester_email})"
                )
            }
        }
        
        # Send notification to Telex 
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEX_WEBHOOK_URL, json=telex_payload)
            response.raise_for_status()

        return {"message": "Sent to Telex", "telex_payload": telex_payload}
    
    except httpx.RequestError as req_error:
        return {"error": "Failed to send request to Telex", "details": str(req_error)}
    
    except Exception as e:
        return {"error": "Unexpected error occurred", "details": str(e)}
