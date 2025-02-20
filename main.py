import hashlib
import hmac
import logging
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],  
    allow_headers=["*"],
)

# Retrieve Telex & Zendesk webhook details
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"
ZENDESK_WEBHOOK_SECRET = os.getenv("ZENDESK_WEBHOOK_SECRET")

if not ZENDESK_WEBHOOK_SECRET:
    raise ValueError("ZENDESK_WEBHOOK_SECRET is not set in environment variables!")

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request) -> JSONResponse:
    try:
        # Step 1: Retrieve raw request body
        body = await request.body()

        # Step 2: Extract Zendesk signature from headers
        zendesk_signature = request.headers.get("X-Zendesk-Webhook-Signature")
        if not zendesk_signature:
            logging.warning("Missing Zendesk signature in request headers")
            raise HTTPException(status_code=401, detail="Missing Zendesk signature")

        # Step 3: Compute expected HMAC-SHA256 signature
        computed_signature = hmac.new(
            key=ZENDESK_WEBHOOK_SECRET.encode(),
            msg=body,
            digestmod=hashlib.sha256
        ).hexdigest()

        # Step 4: Compare the computed signature with the received one
        if not hmac.compare_digest(computed_signature, zendesk_signature):
            logging.warning("Invalid Zendesk signature. Possible spoofed request.")
            raise HTTPException(status_code=403, detail="Invalid Zendesk signature")

        # Step 5: Parse JSON data
        data = await request.json()
        ticket = data.get("ticket", {})

        # Validate required fields
        if not ticket:
            raise KeyError("Missing 'ticket' data in request.")

        # Extract ticket details safely
        ticket_id = str(ticket.get("id", "Unknown"))
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")

        # Construct payload for Telex
        telex_payload = {
            "event": "message",
            "data": {
                "text": f"🎫 **Ticket #{ticket_id} Updated!**\n📌 **Subject:** {subject}\n🔘 **Status:** {status}\n⚡ **Priority:** {priority}\n👤 **Requester:** {requester_email}"
            }
        }

        logging.info(f"Sending to Telex: {telex_payload}")

        # Step 6: Send to Telex.im
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

            return JSONResponse(
                content={"message": "Sent to Telex", "telex_payload": telex_payload},
                status_code=200
            )

    except KeyError as e:
        logging.error(f"Missing key in request data: {str(e)}")
        return JSONResponse(content={"error": f"Invalid data: {str(e)}"}, status_code=400)

    except httpx.RequestError as e:
        logging.error(f"Failed to send request to Telex: {str(e)}")
        return JSONResponse(content={"error": "Failed to send request to Telex"}, status_code=500)

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)

# # from fastapi import FastAPI, Request
# # import httpx

# # app = FastAPI()

# WEBHOOK_URL = "https://ping.telex.im/v1/webhooks/0195154a-3c62-7f11-9cb0-8e892cd7d3ce"

# @app.post("/test")
# async def test_endpoint():
#     payload = {
#         "event_name": "Zendesk integration",
#         "message": "Zendesk test",
#         "status": "success",
#         "username": "Nana"
#     }

#     headers = {
#         "Accept": "application/json",
#         "Content-Type": "application/json"
#     }

#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
#             response.raise_for_status()  # Raise an exception for 4xx/5xx errors
#             return {"status": "success", "response": response.json()}
#         except httpx.HTTPStatusError as e:
#             return {"status": "error", "message": f"HTTP error: {e.response.status_code}", "details": e.response.text}
#         except httpx.RequestError as e:
#             return {"status": "error", "message": "Request failed", "details": str(e)}

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)