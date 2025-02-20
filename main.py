import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()
app = FastAPI(root_path="/")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],  
    allow_headers=["*"],
)

# Telex Webhook Details
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request):
    try:
        data = await request.json()
        ticket = data.get("ticket", {})

        # Extract ticket details
        ticket_id = ticket.get("id", "Unknown")
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        
        payload = {
            "event_name": f"Ticket #{ticket_id}",
            "message": f"{subject} - {requester_email}",
            "status": "success",
            "username": requester.get("name", "Unknown")
        }

        # Send notification to Telex
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TELEX_WEBHOOK_URL,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return response.json()

    except httpx.RequestError as req_error:
        return {"error": "Failed to send request to Telex", "details": str(req_error)}
    
    except Exception as e:
        return {"error": "Unexpected error occurred", "details": str(e)}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True)