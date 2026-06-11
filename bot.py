import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# Configurable Global Variables (Fill these in before running)
BOT_TOKEN = "8895397749: AAFN8P4ZS9560jj4P11z_bJ-
BcvQiZTVCtA"  # Put your Telegram Bot Token here (e.g., "123456:ABC-def...")
EXTERNAL_API_URL = "34118021"  # Put your OSINT Phone API endpoint here

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Basic memory tracker to catch the user's workflow state per chat session
# State 0 = Idle/Start, State 1 = Awaiting 10-digit Phone Number
USER_STATES = {}


# ==========================================
# 1. DUMMY HTTP SERVER (For deployment/ping checks)
# ==========================================
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        response_message = (
            "<html><body><h1>Bot Status: Operational</h1></body></html>"
        )
        self.wfile.write(response_message.encode("utf-8"))

    def log_message(self, format, *args):
        # Overridden to suppress default logging noise in console
        return


def run_dummy_server():
    server_address = ("", 8080)
    httpd = HTTPServer(server_address, DummyServerHandler)
    print("🌍 Dummy HTTP server running silently on port 8080...")
    httpd.serve_forever()


# ==========================================
# 2. TELEGRAM API MANUAL WRAPPERS
# ==========================================
def send_message(chat_id, text, reply_markup=None):
    """Manually executes a sendMessage POST request."""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return None


def get_updates(offset=None):
    """Manually fetches incoming telemetry via getUpdates."""
    url = f"{BASE_URL}/getUpdates"
    payload = {"timeout": 30}  # Long polling timeout configuration
    if offset:
        payload["offset"] = offset

    try:
        response = requests.post(url, json=payload, timeout=35)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        # Network hiccup or timeout; return empty structure safely
        return None
    return None


# ==========================================
# 3. MESSAGE CORE ROUTER
# ==========================================
def handle_message(chat_id, text):
    global USER_STATES
    text_clean = text.strip()

    # Define the persistent Custom Keyboard Markup Structure
    custom_keyboard = {
        "keyboard": [[{"text": "📱 Phone Lookup"}]],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }

    # Routine A: Check for commands or explicit interaction requests
    if text_clean == "/start":
        USER_STATES[chat_id] = 0
        welcome_msg = (
            "🕵️‍♂️ <b>OSINT Terminal Active</b>\n\n"
            "Welcome! Use the interactive menu button below to scan targets manually."
        )
        send_message(chat_id, welcome_msg, reply_markup=custom_keyboard)
        return

    elif text_clean == "📱 Phone Lookup":
        USER_STATES[chat_id] = 1  # Elevate target state to await input
        prompt_msg = "📞 Send 10 digit mobile number:"
        send_message(chat_id, prompt_msg)
        return

    # Routine B: Evaluate State-based response tracking
    current_state = USER_STATES.get(chat_id, 0)

    if current_state == 1:
        # Regex sanitization checking for exact 10-digit number structure
        if re.fullmatch(r"\d{10}", text_clean):
            send_message(chat_id, "🔍 Searching intelligence databases...")

            # Fallback mock payload if target environment endpoint variables remain blank
            if not EXTERNAL_API_URL:
                mock_intel = {
                    "status": "success",
                    "target": text_clean,
                    "intel": {
                        "carrier": "Mock Carrier Communications Inc.",
                        "type": "Mobile",
                        "valid": True,
                        "reputation": "Clean",
                    },
                }
                formatted_json = json.dumps(mock_intel, indent=4)
                response_payload = (
                    f"<pre>{formatted_json}</pre>\n\n"
                    f"⚠️ <i>Note: EXTERNAL_API_URL variable is empty. Displaying internal sandbox mock telemetry.</i>"
                )
            else:
                try:
                    # Construct query params or adapt structure depending on target endpoint specifications
                    api_resp = requests.get(
                        EXTERNAL_API_URL,
                        params={"phone": text_clean},
                        timeout=10,
                    )
                    raw_json = api_resp.json()
                    formatted_json = json.dumps(raw_json, indent=4)
                    response_payload = f"<pre>{formatted_json}</pre>"
                except Exception as api_err:
                    response_payload = (
                        f"❌ <b>API Error Encountered:</b>\n{str(api_err)}"
                    )

            # Revert session state safely to Idle state upon cycle completion
            USER_STATES[chat_id] = 0
            send_message(chat_id, response_payload, reply_markup=custom_keyboard)

        else:
            # Input failed criteria. Persist within tracking State 1 loop until cleared properly
            error_msg = "❌ <b>Invalid Input!</b> Please make sure you enter exactly 10 digits without any text, spaces, or country codes (e.g., 5557778888)."
            send_message(chat_id, error_msg)


# ==========================================
# 4. MAIN LONG POLLING INITIALIZATION LOOP
# ==========================================
if __name__ == "__main__":
    # Validate token structure presence before loop allocation
    if not BOT_TOKEN:
        print(
            "🛑 ERROR: Your BOT_TOKEN variable is completely blank!\n"
            "Please paste a valid Telegram API token from @BotFather into line 9."
        )
        exit(1)

    # Launch background HTTP Thread
    server_thread = threading.Thread(target=run_dummy_server, daemon=True)
    server_thread.start()

    print("🤖 Bot engine initialized successfully.")
    print("📡 Manually listening for long-polling telemetry pipeline updates...")

    update_offset = None

    while True:
        updates_data = get_updates(offset=update_offset)

        if updates_data and updates_data.get("ok"):
            for update in updates_data.get("result", []):
                update_id = update["update_id"]
                # Bump the current loop tracking offset immediately to acknowledge transaction logs
                update_offset = update_id + 1

                if "message" in update:
                    message_obj = update["message"]
                    chat_id = message_obj["chat"]["id"]

                    # Only handle events matching processing pipeline expectations (Text entries)
                    if "text" in message_obj:
                        incoming_text = message_obj["text"]
                        handle_message(chat_id, incoming_text)

        # Gentle throttling threshold step to mitigate processing load spikes
        time.sleep(0.5)
