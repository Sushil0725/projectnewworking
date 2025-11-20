import time
import requests
import subprocess
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
ESP32_IP = "http://192.168.1.214"
OLLAMA_MODEL = "llama3:latest" 

# Priority System
last_manual_time = 0
MANUAL_OVERRIDE_DURATION = 3.0 

# ================= HELPERS =================
def send_to_esp(action):
    try:
        requests.get(f"{ESP32_IP}/cmd?action={action}", timeout=0.2)
        return True
    except:
        return False

def ask_ollama_smart(text):
    """
    Asks AI for BOTH a command AND a witty reply.
    Format expected from AI: COMMAND | REPLY
    """
    system_prompt = (
        "You are Jarvis, a loyal robot assistant. "
        "Analyze the user's input. "
        "1. Identify the command: forward, backward, left, right, stop, or none. "
        "2. Generate a short, cool, robotic reply. "
        "Output format: COMMAND | REPLY "
        "Example 1: 'Jarvis, move forward' -> forward | Advancing now, sir. "
        "Example 2: 'Turn around' -> backward | Initiating reverse maneuvers. "
        "Example 3: 'Hello' -> none | Systems online. Awaiting orders. "
        "Reply ONLY with the output string."
    )
    
    full_prompt = f"{system_prompt}\nUser: {text}\nOutput:"
    
    try:
        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL, full_prompt],
            capture_output=True, text=True, encoding='utf-8'
        )
        output = result.stdout.strip()
        
        # Split the result (COMMAND | REPLY)
        if "|" in output:
            parts = output.split("|")
            return parts[0].strip().lower(), parts[1].strip()
        else:
            # Fallback if AI messes up formatting
            return "none", output
    except:
        return "none", "I am having trouble thinking, sir."

# ================= ROUTES =================

@app.route('/')
def home():
    return "Jarvis 2.0 Online. <a href='/face'>iPad Face</a> | <a href='/remote'>Phone Remote</a>"

@app.route('/face')
def face_ui():
    return render_template('face.html')

@app.route('/remote')
def remote_ui():
    return render_template('remote.html')

@app.route('/manual_input', methods=['GET'])
def manual_input():
    global last_manual_time
    action = request.args.get('action')
    last_manual_time = time.time()
    send_to_esp(action)
    return jsonify({"status": "executed"})

@app.route('/voice_input', methods=['POST'])
def voice_input():
    global last_manual_time
    
    # 1. Check Priority (Phone overrides Voice)
    if time.time() - last_manual_time < MANUAL_OVERRIDE_DURATION:
        return jsonify({"reply": "Manual override engaged. Voice ignored.", "command": "none"})

    data = request.json
    user_text = data.get('text', '').lower()
    print(f"🎤 Heard: {user_text}")

    # 2. Ask AI for Command + Reply
    command, reply = ask_ollama_smart(user_text)

    # 3. Execute Command
    valid_moves = ["forward", "backward", "left", "right", "stop"]
    if command in valid_moves:
        print(f"🤖 ACTION: {command}")
        send_to_esp(command)

    return jsonify({"reply": reply, "command": command})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)