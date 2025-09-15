# agent_state.py
import time

# ---------------- State ----------------
is_awake = True   # Bot starts awake
last_interaction = time.time()
timeout_seconds = 180  # 3 minutes

# ---------------- Keywords ----------------
wake_word = "hi clara"
sleep_phrase = "don't talk anything"


# ---------------- State Functions ----------------
def wake_up():
    """Wake the bot up via voice or manual trigger."""
    global is_awake, last_interaction
    is_awake = True
    last_interaction = time.time()
    return "✅ Wake word detected. Clara is now active."


def go_to_sleep(auto=False):
    """Put the bot to sleep manually or after inactivity."""
    global is_awake
    is_awake = False
    if auto:
        return "⏳ No interaction for 3 minutes. Clara is going to sleep."
    return "😴 Sleep command detected. Clara will now stay silent until you say 'hi clara'."


def update_activity():
    """Update activity timestamp whenever user interacts."""
    global last_interaction
    last_interaction = time.time()


def check_auto_sleep():
    """Check if bot should auto-sleep due to inactivity."""
    global is_awake, last_interaction
    if is_awake and (time.time() - last_interaction > timeout_seconds):
        return go_to_sleep(auto=True)
    return None
