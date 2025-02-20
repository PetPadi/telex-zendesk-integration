from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
import os
import uvicorn

load_dotenv()

# Initialize FastAPI without root_path
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],  # Added OPTIONS for preflight
    allow_headers=["*"],
)

TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        ticket = data.get("ticket", {})
        
        # Extract ticket details
        ticket_id = str(ticket.get("id", "Unknown"))
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        
        telex_payload = {
            "channel": TELEX_CHANNEL_ID,
            "event": "message",
            "data": {
                "text": f"Ticket #{ticket_id} Updated!\nSubject: {subject}\nStatus: Unknown\nPriority: Unknown\nRequester: {requester_email}"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TELEX_WEBHOOK_URL,
                json=telex_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                follow_redirects=True  # Handle any redirects automatically
            )
            response.raise_for_status()
            
            return JSONResponse(
                content={
                    "message": "Sent to Telex",
                    "telex_payload": telex_payload
                },
                status_code=200
            )
            
    except httpx.RequestError as e:
        return JSONResponse(
            content={"error": f"Failed to send request to Telex: {str(e)}"},
            status_code=500
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Unexpected error: {str(e)}"},
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)