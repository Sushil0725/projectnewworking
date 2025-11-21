import time
import requests
import subprocess
import datetime
import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
ESP32_IP = "http://192.168.1.214"
GOOGLE_API_KEY = "AIzaSyDx7lJVT181Tm2xsxTdC8EOU2EBL8VxmmA" 

# Model Setup
GEMINI_MODEL_NAME = "gemini-2.5-flash"
OLLAMA_MODEL = "llama3:latest" 

model = None
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print(f"✅ Gemini Service Connected: {GEMINI_MODEL_NAME}")
except Exception as e:
    print(f"⚠️ Gemini Init Error: {e}")

# --- MEMORY (Last 5 Exchanges) ---
chat_history = []
MAX_HISTORY = 10 

# --- STATE ---
USE_GEMINI_BACKEND = True  
VOICE_SYSTEM_MUTED = False 
MANUAL_MODE_LOCKED = False 
last_manual_time = 0
MANUAL_OVERRIDE_DURATION = 3.0 

# ================= 1. INSTANT ANSWERS (MODE 2) =================
FAST_RESPONSES = {
    "who are you": "I am Sonic, your advanced robot assistant.",
    "what is your name": "My name is Sonic.",
    "what are you": "I am a hybrid AI robot capable of movement and conversation.",
    "who created you": "I was created by a brilliant engineer.",
    "hello": "Systems online. Ready for input.",
    "hi": "Hello there.",
    "status": "All systems operational.",
    "how are you": "I am functioning at 100 percent efficiency."
}

# ================= 2. SYSTEM PROMPT (MODES 1 & 3) =================
def get_system_prompt():
    current_time = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    return (
        f"You are Sonic, a smart robot assistant. Time: {current_time}. "
        "Analyze input. Output ONLY the raw string in this strict format: TYPE | ACTION | REPLY"
        "\n\n"
        "MODE 1: ROBOT COMMAND (Moving/Stopping)"
        "\n- Triggers: forward, back, left, right, stop, spin, roll."
        "\n- Format: COMMAND | [action] | [short confirmation]"
        "\n- Example: COMMAND | forward | Advancing."
        "\n\n"
        "MODE 3: KNOWLEDGE & QUESTIONS (Everything else)"
        "\n- Format: QUESTION | none | [concise answer]"
        "\n- Note: Use the history context. Keep answers short (max 2 sentences)."
        "\n- Example: QUESTION | none | The capital of France is Paris."
        "\n\n"
        "CRITICAL RULES:"
        "\n- Do NOT output labels like 'Mode 1:' or 'Answer:'."
        "\n- Do NOT include the reasoning."
        "\n- Start the string immediately with the TYPE."
    )

# ================= HELPERS =================
def send_to_esp(action):
    try:
        requests.get(f"{ESP32_IP}/cmd?action={action}")
        return True
    except Exception as e:
        print(f"❌ Robot Error: {e}")
        return False

def update_history(role, text):
    global chat_history
    chat_history.append(f"{role}: {text}")
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)

# ================= AI ENGINES =================
def ask_gemini(user_text):
    try:
        print("\n" + "="*30)
        print(f"🚀 USING CLOUD GEMINI ({GEMINI_MODEL_NAME})")
        
        history_block = "\n".join(chat_history)
        full_prompt = f"{get_system_prompt()}\n\n--- HISTORY ---\n{history_block}\n\n--- NEW INPUT ---\nUser: {user_text}\nOUTPUT:"
        
        print("-" * 10 + " SENDING PROMPT " + "-" * 10)
        print(full_prompt)
        print("-" * 36)

        response = model.generate_content(full_prompt)
        
        if response.text: 
            print("-" * 10 + " RAW REPLY " + "-" * 10)
            print(response.text.strip())
            print("="*30 + "\n")
            return parse_ai_response(response.text)
        return None
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return None 

def ask_ollama(user_text):
    try:
        print("\n" + "="*30)
        print(f"🐢 USING LOCAL OLLAMA ({OLLAMA_MODEL})")
        
        history_block = "\n".join(chat_history)
        full_prompt = f"{get_system_prompt()}\n\nHISTORY:\n{history_block}\n\nUSER: {user_text}\nOUTPUT:"
        
        print("-" * 10 + " SENDING PROMPT " + "-" * 10)
        print(full_prompt)
        print("-" * 36)

        result = subprocess.run(["ollama", "run", OLLAMA_MODEL, full_prompt], capture_output=True, text=True, encoding='utf-8')
        
        print("-" * 10 + " RAW REPLY " + "-" * 10)
        print(result.stdout.strip())
        print("="*30 + "\n")

        return parse_ai_response(result.stdout)
    except:
        return "none", "System failure."

def parse_ai_response(text):
    text = text.strip()
    
    # Cleanup
    bad_prefixes = ["Output:", "Response:", "Mode 1:", "Mode 2:", "Mode 3:"]
    for prefix in bad_prefixes:
        if text.startswith(prefix):
            text = text.replace(prefix, "").strip()

    try:
        parts = text.split("|")
        if len(parts) >= 3: 
            return parts[1].strip().lower(), parts[2].strip()
        elif len(parts) == 2: 
            return parts[0].strip().lower(), parts[1].strip()
        else: 
            return "none", text
    except: 
        return "none", text

# ================= ROUTES =================

@app.route('/')
def home():
    return "Sonic Core 12.0. <a href='/face'>iPad</a> | <a href='/remote'>Phone</a>"

@app.route('/face')
def face_ui():
    return render_template('face.html')

@app.route('/remote')
def remote_ui():
    return render_template('remote.html')

@app.route('/toggle_global_mute')
def toggle_global_mute():
    global VOICE_SYSTEM_MUTED
    VOICE_SYSTEM_MUTED = not VOICE_SYSTEM_MUTED
    status = "MUTED" if VOICE_SYSTEM_MUTED else "LISTENING"
    print(f"🔕 GLOBAL MUTE: {status}")
    return jsonify({"status": status, "muted": VOICE_SYSTEM_MUTED})

@app.route('/toggle_manual_lock')
def toggle_manual_lock():
    global MANUAL_MODE_LOCKED
    MANUAL_MODE_LOCKED = not MANUAL_MODE_LOCKED
    status = "LOCKED" if MANUAL_MODE_LOCKED else "UNLOCKED"
    print(f"🔒 MANUAL OVERRIDE: {status}")
    return jsonify({"status": status, "locked": MANUAL_MODE_LOCKED})

@app.route('/manual_input', methods=['GET'])
def manual_input():
    action = request.args.get('action')
    send_to_esp(action)
    return jsonify({"status": "executed"})

@app.route('/voice_input', methods=['POST'])
def voice_input():
    global USE_GEMINI_BACKEND
    
    if VOICE_SYSTEM_MUTED:
        return jsonify({"reply": "", "command": "none"})
    if MANUAL_MODE_LOCKED:
        return jsonify({"reply": "Controls locked.", "command": "none"})

    data = request.json
    user_text = data.get('text', '').strip()
    clean_text = user_text.lower().replace("?", "").replace(".", "").strip() 
    
    if not user_text: return jsonify({"reply": "", "command": "none"})

    print(f"🎤 User: {user_text}")
    update_history("User", user_text)

    # 1. FAST TRACK (Instant Answers)
    if clean_text in FAST_RESPONSES:
        reply = FAST_RESPONSES[clean_text]
        print(f"⚡ FAST REPLY: {reply}")
        update_history("Sonic", reply)
        return jsonify({"reply": reply, "command": "none"})

    # 2. AI PROCESSING
    command = "none"
    reply = ""
    
    if USE_GEMINI_BACKEND and model:
        result = ask_gemini(user_text)
        if result:
            command, reply = result
        else:
            print("⚠️ Gemini failed. Switching to Local Mode (Silent).")
            USE_GEMINI_BACKEND = False
            command, reply = ask_ollama(user_text)
    else:
        command, reply = ask_ollama(user_text)

    # 3. EXECUTION
    valid_moves = ["forward", "backward", "left", "right", "stop"]
    
    if command in valid_moves:
        print(f"🤖 COMMAND: {command}")
        send_to_esp(command)
    else:
        print(f"💬 CHAT: {reply}")
    
    update_history("Sonic", reply)
    return jsonify({"reply": reply, "command": command})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)