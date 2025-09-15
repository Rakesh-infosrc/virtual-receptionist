import os
import uvicorn
import time
import random
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from livekit import api  # Correct LiveKit import

# Load environment variables from .env
load_dotenv()

API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://127.0.0.1:7880")

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/get-token")
def get_token(identity: str = Query(...), room: str = "Clara-room"):
    """
    Generate a LiveKit access token for the given identity.
    Handles reconnects by generating unique identities per session.
    """
    try:
        # Generate a unique session identity
        session_identity = f"{identity}_{random.randint(1000,9999)}"

        # Create AccessToken
        at = api.AccessToken(API_KEY, API_SECRET)
        at.identity = session_identity

        # Set token expiration to 1 hour from now
        at.expires_at = int(time.time()) + 3600

        # Add video grant to allow joining the room
        video_grants = api.VideoGrants(room=room, room_join=True)
        at.with_grants(video_grants)

        # Generate JWT token
        token = at.to_jwt()

        print(f"✅ Issued token for {session_identity} in room {room}")
        return {"token": token, "url": LIVEKIT_URL, "room": room}

    except Exception as e:
        print("❌ Error issuing token:", str(e))
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
