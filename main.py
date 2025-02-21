import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
import json  # NEW: Added for pretty printing logs

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# NEW: Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        # NEW: Log incoming request
        logger.info("Received webhook request from Zendesk")
        
        # Parse JSON data
        data = await request.json()
        # NEW: Log incoming data
        logger.info("Incoming Zendesk data: %s", json.dumps(data, indent=2))
        
        ticket = data.get("ticket", {})

        # Validate required fields
        if not ticket:
            logger.error("Missing ticket data in request")  # NEW: Added error logging
            raise KeyError("Missing 'ticket' data in request.")

        # Extract ticket details safely
        ticket_id = str(ticket.get("id", "Unknown"))
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")

        # NEW: Log extracted ticket details
        logger.info(
            "Extracted ticket details:\n"
            f"Ticket ID: {ticket_id}\n"
            f"Subject: {subject}\n"
            f"Status: {status}\n"
            f"Priority: {priority}\n"
            f"Requester: {requester_email}"
        )

        # Construct payload for Telex
        telex_payload = {
            "event": "message",
            "data": {
                "text": f"🎫 **Ticket #{ticket_id} Updated!**\n📌 **Subject:** {subject}\n🔘 **Status:** {status}\n⚡ **Priority:** {priority}\n👤 **Requester:** {requester_email}"
            }
        }

        # NEW: Log Telex payload
        logger.info("Sending payload to Telex: %s", json.dumps(telex_payload, indent=2))

        # Send to Telex.im
        async with httpx.AsyncClient() as client:
            # NEW: Log the request to Telex
            logger.info(f"Sending request to Telex URL: {TELEX_WEBHOOK_URL}")
            
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
            
            # NEW: Log Telex response
            logger.info(f"Telex response status code: {response.status_code}")
            logger.info(f"Telex response content: {response.text}")

            return JSONResponse(
                content={"message": "Sent to Telex", "telex_payload": telex_payload},
                status_code=200
            )

    except KeyError as e:
        error_msg = f"Missing key in request data: {str(e)}"
        logger.error(error_msg)  # NEW: Enhanced error logging
        return JSONResponse(content={"error": error_msg}, status_code=400)

    except httpx.RequestError as e:
        error_msg = f"Failed to send request to Telex: {str(e)}"
        logger.error(error_msg)  # NEW: Enhanced error logging
        return JSONResponse(content={"error": error_msg}, status_code=500)

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)  # NEW: Enhanced error logging
        return JSONResponse(content={"error": error_msg}, status_code=500)

# # # from fastapi import FastAPI, Request
# # # import httpx

# # # app = FastAPI()

# # WEBHOOK_URL = "https://ping.telex.im/v1/webhooks/0195154a-3c62-7f11-9cb0-8e892cd7d3ce"

# # @app.post("/test")
# # async def test_endpoint():
# #     payload = {
# #         "event_name": "Zendesk integration",
# #         "message": "Zendesk test",
# #         "status": "success",
# #         "username": "Nana"
# #     }

# #     headers = {
# #         "Accept": "application/json",
# #         "Content-Type": "application/json"
# #     }

# #     async with httpx.AsyncClient() as client:
# #         try:
# #             response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
# #             response.raise_for_status()  # Raise an exception for 4xx/5xx errors
# #             return {"status": "success", "response": response.json()}
# #         except httpx.HTTPStatusError as e:
# #             return {"status": "error", "message": f"HTTP error: {e.response.status_code}", "details": e.response.text}
# #         except httpx.RequestError as e:
# #             return {"status": "error", "message": "Request failed", "details": str(e)}

# # if __name__ == "__main__":
# #     uvicorn.run(app, host="0.0.0.0", port=8000)