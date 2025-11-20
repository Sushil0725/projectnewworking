import time
import requests
import subprocess
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
# ESP32 Static IP (Must match the code in Arduino)
ESP32_IP = "http://192.168.1.214"

# AI Model
OLLAMA_MODEL = "llama3:latest" 

# PRIORITY SYSTEM
# If a manual button is pressed, ignore voice for 3 seconds
last_manual_time = 0
MANUAL_OVERRIDE_DURATION = 3.0 

# ================= HELPERS =================
def send_to_esp(action):
    """Sends command to the robot muscles"""
    try:
        url = f"{ESP32_IP}/cmd?action={action}"
        # Set a tiny timeout so we don't freeze if robot disconnects
        requests.get(url, timeout=0.2) 
        print(f"🤖 SENT TO ROBOT: {action}")
        return True
    except:
        print(f"❌ FAILED: Robot at {ESP32_IP} is not responding")
        return False

def get_ai_intent(text):
    """Asks Ollama to convert speech to a command"""
    prompt = (
        f"Map this text to one command: forward, backward, left, right, stop. "
        f"Text: '{text}'. Reply ONLY with the command word. If irrelevant, reply 'chat'."
    )
    try:
        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL, prompt],
            capture_output=True, text=True, encoding='utf-8'
        )
        return result.stdout.strip().lower()
    except:
        return "chat"

# ================= ROUTES (PAGES) =================

@app.route('/')
def home():
    return "Jarvis Server Online. Go to /face (iPad) or /remote (Phone)."

@app.route('/face')
def face_ui():
    # This serves the Face UI for the iPad
    return render_template('face.html')

@app.route('/remote')
def remote_ui():
    # This serves the Joystick UI for the Phone
    return render_template('remote.html')

# ================= ROUTES (API) =================

@app.route('/manual_input', methods=['GET'])
def manual_input():
    """High Priority: Remote Control Input"""
    global last_manual_time
    action = request.args.get('action')
    
    # Update timestamp to block voice commands
    last_manual_time = time.time()
    
    send_to_esp(action)
    return jsonify({"status": "executed", "source": "manual"})

@app.route('/voice_input', methods=['POST'])
def voice_input():
    """Low Priority: iPad Voice Input"""
    global last_manual_time
    
    # 1. Check Priority
    if time.time() - last_manual_time < MANUAL_OVERRIDE_DURATION:
        print("⚠️ Voice ignored (Manual Override Active)")
        return jsonify({"reply": "Manual control active, ignoring voice."})

    data = request.json
    user_text = data.get('text', '').lower()
    print(f"🎤 Heard: {user_text}")

    # 2. Keyword Fast-Path (Faster than AI)
    command = "chat"
    if "stop" in user_text: command = "stop"
    elif "forward" in user_text or "go" in user_text: command = "forward"
    elif "back" in user_text: command = "backward"
    elif "left" in user_text: command = "left"
    elif "right" in user_text: command = "right"
    else:
        # 3. Ask AI if no keyword found
        command = get_ai_intent(user_text)

    # 4. Execute
    valid_moves = ["forward", "backward", "left", "right", "stop"]
    reply = ""
    
    if command in valid_moves:
        send_to_esp(command)
        reply = f"Executing {command}"
    else:
        reply = "Standing by."

    return jsonify({"reply": reply, "command": command})

if __name__ == '__main__':
    # Host 0.0.0.0 allows other devices on WiFi to connect
    app.run(host='0.0.0.0', port=5000, debug=True)