import os
from dotenv import load_dotenv
import logging
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation, google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from agent_state import is_awake, check_auto_sleep
from tools import (
    get_weather,
    send_email,
    search_web,
    listen_for_commands,
    company_info,
    get_employee_details,
    get_candidate_details,
    log_and_notify_visitor,
)

# Load environment variables
load_dotenv()

# Set logging to INFO to reduce noise
logging.basicConfig(level=logging.INFO)


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.7,
            ),
            tools=[
                company_info,
                get_employee_details,
                get_candidate_details,
                listen_for_commands,
                get_weather,
                search_web,
                send_email,
                log_and_notify_visitor,
            ],
        )


async def entrypoint(ctx: agents.JobContext):
    # Initialize AgentSession
    session = AgentSession()

    # # Initialize Tavus AvatarSession (left untouched as per your request)
    # avatar = tavus.AvatarSession(
    #     replica_id=os.environ.get("REPLICA_ID"),
    #     persona_id=os.environ.get("PERSONA_ID"),
    #     api_key=os.environ.get("TAVUS_API_KEY"),
    # )
    # await avatar.start(session, room=ctx.room)

    # Room input options
    room_options = RoomInputOptions(
        video_enabled=True,
        noise_cancellation=noise_cancellation.BVC(),
    )

    # Start the Agent session
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=room_options,
    )

    # Connect context
    await ctx.connect()

    # ⏳ Auto-sleep check (3 min inactivity)
    auto_sleep_msg = check_auto_sleep()
    if auto_sleep_msg:
        print(auto_sleep_msg)
        return

    # ✅ Only reply if bot is awake
    if is_awake:
        await session.generate_reply(
            instructions=SESSION_INSTRUCTION,
        )
    else:
        print("🤫 Clara is sleeping. Ignoring all inputs until you say 'hi clara'.")


# Print Tavus API key at startup (for debug)
print("Tavus API Key being used:", os.getenv("TAVUS_API_KEY"))

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )
