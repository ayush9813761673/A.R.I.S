# ==========================================================
#        A.R.I.S - All-in-one Modular Assistant
# ==========================================================
# PHASE 2 PLANNED UPGRADES:
#   - Recurring events support for Google Calendar integration
#   - Emotional memory-based replies (contextual, mood-aware)
#   - Personalized suggestions (habit learning, proactive ideas)
#   - Full calendar view with spoken summary
#   - Real-time task feedback based on mood/emotion analysis
# ==========================================================
# 🔥 Phase 1: Habit Learning & Prediction (Completed)
#   - Habit logger added: Tracks command usage, timestamps, frequency
#
# 🔥 Phase 2: Calendar Sync & Proactive Reminders (2.3 & 2.4 Complete)
#   - Voice reminders trigger before events (3-min alert)
#   - Calendar events can be created/edited via voice
#
# 🔥 Phase 3: Dynamic Voice Styles (Started)
#   - Mood-based voice switching logic embedded (Pitch/speed coming next)
# ==========================================================
#
# CHANGELOG (Current Version):
#   - Added Google Calendar integration (OAuth, event creation)
#   - Added trigger file support for shortcut command execution
#   - Added real-time emotion UI (OpenCV window, console fallback)
#   - Modular code cleanup and optimization for maintainability
#
# ==========================================================
# --------------------------
# A.R.I.S - All-in-one Modular Assistant
# --------------------------
import os
import pyttsx3
import edge_tts
import asyncio
import tempfile
import webbrowser
import subprocess
import pyaudio
import speech_recognition as sr
from pptx import Presentation
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
load_dotenv()
import smtplib
from email.message import EmailMessage
from llama_cpp import Llama
from datetime import datetime
import mimetypes
import time
import glob
import json
import requests
# Camera Mode imports
import cv2
import pytesseract
from PIL import Image
import numpy as np
# FAISS and sentence-transformers for memory
import faiss
from sentence_transformers import SentenceTransformer
# For Google Calendar API
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# For threading (emotion UI)
import threading
# --------------------------
# Memory Manager for FAISS-based semantic memory
# --------------------------
class MemoryManager:
    def __init__(self, embedding_model_name="all-MiniLM-L6-v2"):
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.memories = []  # List of text snippets

    def add_memory(self, text):
        embedding = self.embedding_model.encode([text])
        self.index.add(embedding.astype("float32"))
        self.memories.append(text)

    def retrieve(self, query, top_k=3):
        if len(self.memories) == 0:
            return []
        embedding = self.embedding_model.encode([query]).astype("float32")
        D, I = self.index.search(embedding, top_k)
        results = []
        for idx in I[0]:
            if 0 <= idx < len(self.memories):
                results.append(self.memories[idx])
        return results

# Face recognition import with fallback
try:
    import face_recognition
    FACE_RECO_ENABLED = True
except ImportError:
    print("face_recognition module not found. Face recognition features will be disabled.")
    FACE_RECO_ENABLED = False


# YOLO model setup with auto-download utility
import urllib.request

def download_yolo_files():
    import urllib.request
    print("Checking YOLO files... Downloading if missing.")

    base_url = "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/"
    weight_url = "https://pjreddie.com/media/files/yolov3.weights"
    coco_url = "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"
    yolo_dir = os.path.expanduser("~/yolo")
    os.makedirs(yolo_dir, exist_ok=True)

    yolo_cfg_local = os.path.join(yolo_dir, "yolov3.cfg")
    yolo_weights_local = os.path.join(yolo_dir, "yolov3.weights")
    coco_names_local = os.path.join(yolo_dir, "coco.names")

    try:
        if not os.path.exists(yolo_cfg_local):
            print("Downloading yolov3.cfg...")
            urllib.request.urlretrieve(base_url + "yolov3.cfg", yolo_cfg_local)
        if not os.path.exists(yolo_weights_local):
            print("Downloading yolov3.weights...")
            urllib.request.urlretrieve(weight_url, yolo_weights_local)
        if not os.path.exists(coco_names_local):
            print("Downloading coco.names...")
            urllib.request.urlretrieve(coco_url, coco_names_local)
    except Exception as e:
        print(f"YOLO download failed: {e}")
        return None, None, None

    if not (os.path.exists(yolo_cfg_local) and os.path.exists(yolo_weights_local) and os.path.exists(coco_names_local)):
        print("YOLO files incomplete after download.")
        return None, None, None

    return yolo_cfg_local, yolo_weights_local, coco_names_local

print("Initializing YOLO setup...")
yolo_cfg, yolo_weights, coco_labels_path = download_yolo_files()

if yolo_cfg and yolo_weights:
    try:
        net = cv2.dnn.readNetFromDarknet(yolo_cfg, yolo_weights)
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
    except Exception as e:
        print(f"Failed to load YOLO model: {e}")
        net = None
        output_layers = []
else:
    print("YOLO files not found or download failed, disabling YOLO object detection.")
    net = None
    output_layers = []

# COCO class labels for YOLO
classes = []
if coco_labels_path and os.path.exists(coco_labels_path):
    with open(coco_labels_path, "r") as f:
        classes = [line.strip() for line in f.readlines()]

haar_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_cascade_path)

# --------------------------
# Load Environment Variables
# --------------------------
load_dotenv()

# --------------------------
#
# Core A.R.I.S Class
# --------------------------
class ARIS:
    def __init__(self):
        # ARISGPT Core - Chat history and persona
        self.chat_history = []
        self.max_chat_history = 6
        self.active_voice_profile = None
        self.tts_pitch = 1.0
        self.tts_rate = 1.0
        self.tts_style = "default"
    # ==============================
    # ARISGPT Core - Chat & Persona
    # ==============================
    def build_chat_prompt(self, user_message):
        top_memories = self.memory_manager.retrieve(user_message, top_k=3)
        recent_emotions = self.recent_emotional_context()
        emotion_notes = "\n".join(
            [f"{e['timestamp']}: {e['emotion']} (triggered by '{e['trigger_text']}')" for e in recent_emotions]
        )
        history_snippets = "\n".join(
            [f"You: {u}\nARIS: {a}" for u, a in self.chat_history[-self.max_chat_history:]]
        )
        prompt = f"""
You are ARIS, an emotionally intelligent AI assistant. Use empathy and context to respond.

[Recent Emotional Context]
{emotion_notes}

[Relevant Past Memories]
{top_memories}

[Recent Conversation]
{history_snippets}

[Current User Message]
{user_message}
"""
        return prompt

    async def chat(self, user_message):
        prompt = self.build_chat_prompt(user_message)
        response_obj = self.llm(prompt, max_tokens=250)
        # Support both dict and str return (for compatibility)
        if isinstance(response_obj, dict):
            response = response_obj.get('choices', [{}])[0].get('text', '').strip()
        else:
            response = str(response_obj)
        self.chat_history.append((user_message, response))
        if len(self.chat_history) > self.max_chat_history:
            self.chat_history = self.chat_history[-self.max_chat_history:]
        mood = self.analyze_emotion(response)
        self.speak(response, mood=mood)
        return response

    async def run_arisgpt_mode(self):
        self.speak("ARISGPT is now active. Say 'exit chat' to stop.")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit chat", "stop arisgpt"]:
                self.speak("Exiting ARISGPT mode. Back to normal.")
                break
            await self.chat(user_input)

    def set_voice_persona(self, name):
        profiles = self.load_voice_profiles()
        if name in profiles:
            p = profiles[name]
            self.active_voice_profile = name
            self.tts_pitch = p.get("pitch", 1.0)
            self.tts_rate = p.get("rate", 1.0)
            self.tts_style = p.get("style", "default")
            self.tts_voice = p.get("voice", getattr(self, "tts_voice", self.accent_presets.get(self.active_accent, "en-US-JennyNeural")))
            self.speak(f"Voice persona '{name}' activated.")
        else:
            self.speak(f"Persona '{name}' not found.")

    def load_voice_profiles(self):
        # Loads saved voice profiles from a JSON file
        path = os.path.expanduser("~/.aris_voice_profiles.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
        import os
        # Core Directories and Paths
        self.temp_dir = os.path.expanduser('~/Desktop/A.R.I.S_Photos')
        os.makedirs(self.temp_dir, exist_ok=True)
        self.watch_folder = os.getenv('WATCH_FOLDER_PATH', './watch_folder')

        # Custom Voice Management
        self.custom_voice_dir = os.path.expanduser("~/A.R.I.S_CustomVoices")
        os.makedirs(self.custom_voice_dir, exist_ok=True)
        self.voice_clones = {}  # key: voice name, value: file path or metadata
        self.active_voice_clone = None
        self.accent_presets = {
            "us": "en-US-JennyNeural",
            "uk": "en-GB-RyanNeural",
            "au": "en-AU-NatashaNeural",
            "in": "en-IN-NeerjaNeural"
        }
        self.active_accent = "us"

        # Email Settings
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))

        model_path = os.getenv('LLAMA_MODEL_PATH', '/Users/ayushraj/Models/llama-model/model.bin')
        if not os.path.exists(model_path):
            fallback_path = '/Users/ayushraj/Models/vicuna-q4/vicuna-q4.gguf'
            if os.path.exists(fallback_path):
                print(f"Model not found at {model_path}, using fallback: {fallback_path}")
                model_path = fallback_path
            else:
                print(f"Model not found at {model_path} or fallback at {fallback_path}. Attempting auto-download of Vicuna Q4 GGUF (~4GB)...")
                os.makedirs('/Users/ayushraj/Models/vicuna-q4', exist_ok=True)
                url = "https://huggingface.co/TheBloke/Vicuna-7B-v1.5-GGUF/resolve/main/vicuna-7b-v1.5.Q4_0.gguf"
                dest_path = fallback_path
                import requests
                import time
                def download_with_progress(url, dest):
                    response = requests.get(url, stream=True)
                    total = int(response.headers.get('content-length', 0))
                    start_time = time.time()
                    with open(dest, 'wb') as file, \
                        requests.get(url, stream=True) as r:
                        downloaded = 0
                        for data in r.iter_content(chunk_size=1024*1024):
                            file.write(data)
                            downloaded += len(data)
                            elapsed = time.time() - start_time
                            percent = (downloaded / total) * 100 if total > 0 else 0
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            eta = (total - downloaded) / speed if speed > 0 else 0
                            print(f"\rDownloading Vicuna Q4: {percent:.2f}% ({downloaded//(1024*1024)} MB) - ETA: {int(eta)}s", end='')
                    print("\nDownload complete.")
                try:
                    download_with_progress(url, dest_path)
                    if os.path.exists(dest_path):
                        print(f"Downloaded Vicuna Q4 model to {dest_path}")
                        model_path = dest_path
                    else:
                        raise FileNotFoundError(f"Download failed: {dest_path} not found.")
                except Exception as e:
                    raise FileNotFoundError(
                        f"Automatic download of Vicuna Q4 failed. Please download manually from {url}. Error: {e}"
                    )
        self.llm = Llama(model_path=model_path)

        # Initialize memory manager (semantic memory)
        self.memory_manager = MemoryManager()

        # Meeting Notes
        self.meeting_active = False
        self.meeting_transcript = []

        # Speech Recognizer
        self.recognizer = sr.Recognizer()

        # Initialize TTS engine (pyttsx3) - optional if not using elsewhere
        # self.tts_engine = pyttsx3.init()
        # self.tts_engine.setProperty('rate', 150)  # optional: adjust speaking rate
        # Google Calendar API client
        self.calendar_service = None
        self.init_google_calendar()

        # Real-time emotion state
        self.current_emotion = "default"
        self.emotion_thread_running = True
        self.emotion_thread = threading.Thread(target=self.emotion_ui_loop, daemon=True)
        self.emotion_thread.start()

        self.speak("YO BRO, A.R.I.S is ready!", mood="playful")

    def log_habit(self, command):
        log_path = os.path.expanduser("~/Desktop/aris_habits.json")
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    log = json.load(f)
            else:
                log = {}
            if today not in log:
                log[today] = []
            log[today].append({"command": command, "time": datetime.now().isoformat()})
            with open(log_path, "w") as f:
                json.dump(log, f, indent=2)
        except Exception as e:
            print(f"Habit logging error: {e}")

    # --------------------------
    # Google Calendar API Setup & Event Creation
    # --------------------------
    def init_google_calendar(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None
        token_path = os.path.expanduser('~/.aris_token.pickle')
        creds_path = os.path.expanduser('~/.aris_credentials.json')
        # User should place their OAuth2 credentials JSON at creds_path
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        # If credentials are invalid or don't exist, start OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    print("Google Calendar credentials not found at ~/.aris_credentials.json. Please download from Google Cloud Console.")
                    return
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        try:
            self.calendar_service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            print(f"Could not initialize Google Calendar API: {e}")
            self.calendar_service = None

    def create_calendar_event(self, summary, start_time, end_time, description=""):
        """Create a Google Calendar event. start_time and end_time must be RFC3339 strings."""
        if not self.calendar_service:
            self.speak("Google Calendar API not available. Please check credentials.", mood="sad")
            return
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }
        try:
            event_result = self.calendar_service.events().insert(calendarId='primary', body=event).execute()
            self.speak(f"Event '{summary}' created on your Google Calendar.", mood="happy")
            return event_result
        except Exception as e:
            self.speak(f"Failed to create calendar event: {e}", mood="sad")

    # --------------------------
    # Speak (Console Output + edge-tts) with personality, style, and mood
    # --------------------------
    import random
    import asyncio
    def speak(self, text, mood="default", voice=None, style="cheerful", pitch="+0Hz", rate="+0%"):
        # If mood is not specified (i.e., explicitly None), determine from text.
        if mood is None:
            mood = self.analyze_emotion(text)
        elif mood == "default":
            # If mood is default, try to infer from text for more dynamic mood.
            inferred_mood = self.analyze_emotion(text)
            if inferred_mood != "default":
                mood = inferred_mood
        styles = {
            "default": ["Understood.", "Affirmative.", "Got it.", text],
            "playful": ["You got it, legend!", "Let’s vibe it up!", "Haha, I gotchu!", text],
            "flirty": ["Anything for you, darling.", "You love pushing my buttons, huh?", text],
            "serious": ["Task initiated.", "Running protocol.", "Executing now.", text],
            "happy": ["Glad to help!", "That's awesome!", "I'm happy to assist!", text],
            "sad": ["I'm here if you need me.", "Sorry to hear that.", "Let me know if I can help.", text],
            "angry": ["Let's handle this together.", "Take a deep breath, I'm on it.", text]
        }
        response = random.choice(styles.get(mood, styles["default"]))
        print(f"A.R.I.S: {response}")

        # Determine which voice to use: custom voice clone or accent preset
        tts_voice = None
        if self.active_voice_clone is not None:
            # Placeholder: Use the custom voice clone for TTS
            # In actual implementation, integrate with a voice cloning TTS model or API
            tts_voice = self.active_voice_clone
            # You would route to your custom voice TTS here
            print(f"[DEBUG] Using custom voice clone: {tts_voice}")
            # Placeholder code: just print, or you could play a static sample file for demo
            # For now, fallback to edge-tts with accent preset
            tts_voice = self.accent_presets.get(self.active_accent, "en-US-JennyNeural")
        else:
            tts_voice = self.accent_presets.get(self.active_accent, "en-US-JennyNeural")

        # Dynamic pitch and rate adjustments for mood/tone simulation
        mood_pitch_rate = {
            "happy": ("+2Hz", "+10%"),
            "playful": ("+4Hz", "+15%"),
            "flirty": ("+3Hz", "+5%"),
            "serious": ("-2Hz", "-5%"),
            "sad": ("-4Hz", "-10%"),
            "angry": ("+1Hz", "+20%"),
            "default": ("+0Hz", "+0%"),
        }
        pitch, rate = mood_pitch_rate.get(mood, ("+0Hz", "+0%"))

        async def speak_edge():
            try:
                communicate = edge_tts.Communicate(
                    text=response,
                    voice=tts_voice,
                    style=style,
                    rate=rate,
                    pitch=pitch
                )
                await communicate.play()
            except Exception as e:
                print(f"Edge-TTS error: {e}")
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"])

        asyncio.run(speak_edge())

    # --------------------------
    # Custom Voice Clone Management
    # --------------------------
    def upload_custom_voice(self, file_path):
        """Copy and register a new custom voice sample."""
        import shutil
        if not os.path.exists(file_path):
            self.speak("The specified voice file does not exist.", mood="sad")
            return
        voice_name = os.path.splitext(os.path.basename(file_path))[0]
        dest_path = os.path.join(self.custom_voice_dir, os.path.basename(file_path))
        try:
            shutil.copy2(file_path, dest_path)
            # Placeholder for metadata, could be expanded
            self.voice_clones[voice_name] = dest_path
            self.speak(f"Custom voice '{voice_name}' uploaded and registered.", mood="happy")
        except Exception as e:
            self.speak(f"Failed to upload custom voice: {e}", mood="sad")

    def select_voice_clone(self, voice_name):
        """Set the active custom voice clone."""
        if voice_name in self.voice_clones:
            self.active_voice_clone = self.voice_clones[voice_name]
            self.speak(f"Custom voice '{voice_name}' selected.", mood="happy")
        else:
            self.speak(f"Voice '{voice_name}' not found. Use 'list voices' to see available voices.", mood="sad")

    def list_voice_clones(self):
        """Return a list of available custom voice clones."""
        # Refresh list from directory
        files = [f for f in os.listdir(self.custom_voice_dir) if os.path.isfile(os.path.join(self.custom_voice_dir, f))]
        self.voice_clones = {os.path.splitext(f)[0]: os.path.join(self.custom_voice_dir, f) for f in files}
        if self.voice_clones:
            self.speak("Available custom voices: " + ", ".join(self.voice_clones.keys()), mood="default")
        else:
            self.speak("No custom voices uploaded yet.", mood="sad")
        return list(self.voice_clones.keys())

    def set_accent(self, accent_key):
        """Change the accent preset for TTS."""
        if accent_key in self.accent_presets:
            self.active_accent = accent_key
            self.active_voice_clone = None  # Reset custom voice if switching accent
            self.speak(f"Accent set to {accent_key} ({self.accent_presets[accent_key]}).", mood="happy")
        else:
            self.speak(f"Accent '{accent_key}' not recognized. Available: {', '.join(self.accent_presets.keys())}", mood="sad")

    def analyze_emotion(self, text):
        """Simple keyword-based emotion analysis."""
        text_lower = text.lower()
        happy_keywords = ["happy", "joy", "glad", "awesome", "great", "excited", "yay", "delighted", "wonderful", "love", "fantastic"]
        sad_keywords = ["sad", "unhappy", "depressed", "down", "unfortunate", "sorry", "regret", "disappointed", "blue"]
        angry_keywords = ["angry", "mad", "furious", "annoyed", "hate", "upset", "frustrated", "irritated"]
        for word in happy_keywords:
            if word in text_lower:
                self.log_emotion("happy", text)
                return "happy"
        for word in sad_keywords:
            if word in text_lower:
                self.log_emotion("sad", text)
                return "sad"
        for word in angry_keywords:
            if word in text_lower:
                self.log_emotion("angry", text)
                return "angry"
        self.log_emotion("default", text)
        return "default"

    def log_emotion(self, emotion, text):
        log_path = os.path.expanduser("~/.aris_emotion_log.json")
        data = []
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                data = json.load(f)
        data.append({
            "timestamp": datetime.now().isoformat(),
            "emotion": emotion,
            "trigger_text": text
        })
        with open(log_path, "w") as f:
            json.dump(data, f, indent=2)

    def recent_emotional_context(self, hours=6):
        log_path = os.path.expanduser("~/.aris_emotion_log.json")
        if not os.path.exists(log_path):
            return []
        with open(log_path, "r") as f:
            entries = json.load(f)
        now = datetime.now()
        return [
            e for e in entries
            if (now - datetime.fromisoformat(e["timestamp"])).total_seconds() <= hours * 3600
        ]

    def suggest_proactive_task(self):
        """Suggest a proactive task based on the time of day."""
        now = datetime.now()
        hour = now.hour
        if 5 <= hour < 12:
            self.speak("Good morning! Would you like your daily briefing?", mood="playful")
        elif 12 <= hour < 18:
            self.speak("Good afternoon! Can I help you schedule your tasks or summarize your meetings?", mood="cheerful")
        elif 18 <= hour < 23:
            self.speak("Good evening! Would you like to review your day or hear a creative story?", mood="serious")
        else:
            self.speak("It's late! Let me know if you need anything before you rest.", mood="default")

    # --------------------------
    # Agent Mode++
    # --------------------------
    async def execute_step(self, step):
        step_lower = step.lower()
        if "search" in step_lower:
            query = step_lower.replace("search", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={query}")
            self.speak(f"Searching Google for {query}")
        elif "open" in step_lower:
            app = step_lower.replace("open", "").strip()
            if "youtube" in app:
                webbrowser.open("https://www.youtube.com")
            elif "google" in app:
                webbrowser.open("https://www.google.com")
            elif "spotify" in app:
                webbrowser.open("https://www.spotify.com")
            self.speak(f"Opening {app}")
        elif "create slides" in step_lower:
            await self.create_slides("AI-generated Slide")
        elif "email slide" in step_lower:
            await self.email_file("ai_slide.pptx")
        else:
            self.speak(f"Unknown step: {step}")

    async def run_agent_mode(self, steps):
        self.speak("Running Agent Mode tasks...")
        for step in steps:
            await self.execute_step(step)
            await asyncio.sleep(1)

    # --------------------------
    # Meeting Assistant
    # --------------------------
    def start_meeting(self):
        if self.meeting_active:
            self.speak("Meeting notes already recording.")
            return
        self.meeting_active = True
        self.meeting_transcript = []
        self.speak("Meeting recording started.")

    def stop_meeting(self):
        if not self.meeting_active:
            self.speak("No active meeting to stop.")
            return
        self.meeting_active = False
        filename = os.path.join(self.temp_dir, f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(filename, "w") as f:
            for line in self.meeting_transcript:
                f.write(line + "\n")
        self.speak(f"Meeting transcript saved: {filename}")
        return filename

    def add_meeting_text(self, text):
        if not self.meeting_active:
            self.speak("Meeting not active.")
            return
        self.meeting_transcript.append(text)
        self.speak(f"Added to meeting notes: {text}")

    # --------------------------
    # Email Genius
    # --------------------------
    def draft_email(self, to, subject, body):
        msg = EmailMessage()
        msg['From'] = self.email_address
        msg['To'] = to
        msg['Subject'] = subject
        msg.set_content(body)
        return msg

    def send_email(self, msg):
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            self.speak(f"Email sent to {msg['To']}")
        except Exception as e:
            self.speak(f"Failed to send email: {e}")

    # --------------------------
    # Creative AI Magic
    # --------------------------
    def daily_briefing(self):
        prompt = "Generate a brief daily summary with weather and news."
        response = self.llm(prompt, max_tokens=150)
        briefing = response['choices'][0]['text'].strip()
        self.speak(briefing)
        return briefing

    def creative_story(self, topic):
        prompt = f"Write a short, creative story about {topic}."
        response = self.llm(prompt, max_tokens=250)
        story = response['choices'][0]['text'].strip()
        self.speak(story)
        return story

    # --------------------------
    # File Handling (Slides, Summaries)
    # --------------------------
    async def create_slides(self, title):
        prs = Presentation()
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = title
        slide.placeholders[1].text = "Auto-generated by A.R.I.S"
        file_path = os.path.join(self.temp_dir, "ai_slide.pptx")
        prs.save(file_path)
        self.speak(f"Slide created at {file_path}")
        return file_path

    async def email_file(self, filename):
        file_path = os.path.join(self.temp_dir, filename)
        if not os.path.exists(file_path):
            self.speak("File not found for email.")
            return
        msg = self.draft_email(self.email_address, "Here is your file", "See attached.")
        with open(file_path, "rb") as f:
            data = f.read()
            msg.add_attachment(data, maintype="application",
                               subtype="vnd.openxmlformats-officedocument.presentationml.presentation",
                               filename=filename)
        self.send_email(msg)

    # --------------------------
    # Watch Folder Auto-Process
    # --------------------------
    async def watch_folder_loop(self):
        self.speak(f"Watching folder: {self.watch_folder}")
        processed = set()
        while True:
            # Process .txt files as before
            files = glob.glob(os.path.join(self.watch_folder, '*.txt'))
            new_files = [f for f in files if f not in processed and os.path.basename(f) != "trigger.txt"]
            for file_path in new_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                summary_prompt = f"Summarize this:\n{content}"
                response = self.llm(summary_prompt, max_tokens=100)
                summary = response['choices'][0]['text'].strip()
                summary_file = os.path.join(self.temp_dir, "summary_" + os.path.basename(file_path))
                with open(summary_file, 'w') as f:
                    f.write(summary)
                self.speak(f"Processed and summarized: {file_path}")
                processed.add(file_path)
            # Shortcut trigger support
            trigger_file = os.path.join(self.watch_folder, "trigger.txt")
            if os.path.exists(trigger_file):
                try:
                    with open(trigger_file, "r") as tf:
                        trigger_command = tf.read().strip()
                    self.speak(f"Shortcut trigger detected: {trigger_command}", mood="playful")
                    asyncio.create_task(self.parse_command(trigger_command))
                except Exception as e:
                    self.speak(f"Error reading trigger.txt: {e}")
                try:
                    os.remove(trigger_file)
                except Exception as e:
                    self.speak(f"Could not delete trigger.txt: {e}")
            await asyncio.sleep(3)

    # --------------------------
    # Voice Command Listening
    # --------------------------
    async def listen_and_execute(self):
        with sr.Microphone() as source:
            self.speak("Listening for voice command...")
            audio = self.recognizer.listen(source)
            try:
                command = self.recognizer.recognize_google(audio)
                self.speak(f"You said: {command}")
                result = await self.parse_command(command)
                # If parse_command returns "STOP_VOICE", return it up
                if result == "STOP_VOICE":
                    return "STOP_VOICE"
            except Exception as e:
                self.speak(f"Voice recognition error: {e}")

    # --------------------------
    # Command Parsing
    # --------------------------
    async def parse_command(self, command):
        cmd = command.lower()
        self.log_habit(command)
        # Voice management commands
        if cmd.startswith("upload voice "):
            file_path = command[len("upload voice "):].strip()
            self.upload_custom_voice(file_path)
        elif cmd.startswith("select voice "):
            voice_name = command[len("select voice "):].strip()
            self.select_voice_clone(voice_name)
        elif cmd == "list voices":
            self.list_voice_clones()
        elif cmd.startswith("set accent "):
            accent_key = command[len("set accent "):].strip()
            self.set_accent(accent_key)
        elif cmd.startswith("activate persona"):
            name = cmd.split("activate persona", 1)[1].strip()
            self.set_voice_persona(name)
        elif cmd == "show mood dashboard" or cmd == "show emotion dashboard":
            self.show_mood_dashboard()
        elif cmd.startswith("start arisgpt"):
            asyncio.create_task(self.run_arisgpt_mode())
        # List of recognized "text" commands for memory injection
        else:
            memory_relevant = [
                "hello", "hi", "daily briefing", "create slides", "creative story", "summarize", "story", "briefing"
            ]
            # Google Calendar event creation
            if "create event" in cmd or "schedule meeting" in cmd:
                # Try to extract event details from the command naively (for demo)
                # e.g., "create event Lunch with Bob at 2024-06-05 12:00 for 1 hour"
                import re
                summary = "Untitled Event"
                description = ""
                start_time = None
                end_time = None
                # Regex to extract datetime and duration
                dt_match = re.search(r'at (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', cmd)
                duration_match = re.search(r'for (\d+) (hour|minute)', cmd)
                summary_match = re.search(r'(?:create event|schedule meeting) (.+?)(?: at|$)', cmd)
                if summary_match:
                    summary = summary_match.group(1).strip()
                if dt_match:
                    try:
                        start_dt = datetime.strptime(dt_match.group(1), "%Y-%m-%d %H:%M")
                        start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        start_time = None
                if duration_match and start_time:
                    val = int(duration_match.group(1))
                    unit = duration_match.group(2)
                    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
                    if unit == "hour":
                        end_dt = start_dt + timedelta(hours=val)
                    else:
                        end_dt = start_dt + timedelta(minutes=val)
                    end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
                elif start_time:
                    # Default duration 1 hour
                    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
                    end_dt = start_dt + timedelta(hours=1)
                    end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
                else:
                    # If no time, use now+1h for demo
                    now = datetime.utcnow()
                    start_time = now.strftime("%Y-%m-%dT%H:%M:%S")
                    end_time = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
                self.create_calendar_event(summary, start_time, end_time, description)
            # If command is voice deactivation or control, handle directly
            elif "stop voice" in cmd:
                self.speak("Voice mode deactivated.")
                return "STOP_VOICE"
            elif "start meeting" in cmd:
                self.start_meeting()
            elif "stop meeting" in cmd:
                self.stop_meeting()
            elif "start camera" in cmd or "camera mode" in cmd:
                self.start_camera()
            elif "capture photo" in cmd:
                self.capture_photo()
            elif "scan text" in cmd or "ocr" in cmd:
                self.ocr_last_photo()
            elif "detect faces" in cmd:
                self.detect_faces_in_photo()
            elif "detect objects" in cmd:
                self.detect_objects_in_photo()
            # Memory-aware text commands
            elif any(key in cmd for key in memory_relevant):
                # Add command to memory
                self.memory_manager.add_memory(command)
                # Retrieve relevant past memory
                retrieved = self.memory_manager.retrieve(command, top_k=3)
                memory_context = ""
                if retrieved:
                    memory_context = "\n".join([f"Past memory: {mem}" for mem in retrieved])
                # Build dynamic prompt for Llama
                prompt = ""
                if memory_context:
                    prompt += f"{memory_context}\n"
                prompt += f"Current command: {command}\n"
                prompt += "Respond as A.R.I.S with context from relevant memories if possible."
                # --- Emotion context injection ---
                recent_emotions = self.recent_emotional_context()
                if recent_emotions:
                    emotion_notes = "\n".join([
                        f"{e['timestamp']}: {e['emotion']} (triggered by: '{e['trigger_text']}')" for e in recent_emotions
                    ])
                    prompt = f"[User Emotion History (last 6h)]\n{emotion_notes}\n\n{prompt}"
                # Llama call with memory-injected prompt
                response = self.llm(prompt, max_tokens=200)
                result = response['choices'][0]['text'].strip()
                self.speak(result)
            else:
                self.speak("Command not recognized.")

    # --------------------------
    # Real-Time Emotion Detection UI
    # --------------------------
    def show_mood_dashboard(self):
        # Show a simple dashboard of recent moods/emotions
        recent = self.recent_emotional_context(hours=24)
        if not recent:
            self.speak("No emotion data found for the last 24 hours.")
            return
        mood_counts = {}
        for e in recent:
            mood_counts[e["emotion"]] = mood_counts.get(e["emotion"], 0) + 1
        dashboard = "Mood Dashboard (last 24h):\n"
        for mood, count in mood_counts.items():
            dashboard += f"- {mood}: {count}\n"
        self.speak(dashboard)

    def emotion_ui_loop(self):
        # Use microphone every few seconds, analyze emotion, show in OpenCV window or console
        try:
            import numpy as np
            import collections
            emotion_history = collections.deque(maxlen=5)
            while self.emotion_thread_running:
                try:
                    r = sr.Recognizer()
                    with sr.Microphone() as source:
                        # Listen for 2 seconds of "ambient" audio
                        audio = r.listen(source, phrase_time_limit=2)
                        try:
                            text = r.recognize_google(audio)
                        except Exception:
                            text = ""
                    emotion = self.analyze_emotion(text)
                    self.current_emotion = emotion
                    emotion_history.append(emotion)
                except Exception:
                    self.current_emotion = "default"
                # Display emotion in OpenCV window
                try:
                    img = np.zeros((100, 300, 3), dtype=np.uint8)
                    color = {
                        "happy": (0, 255, 0),
                        "sad": (255, 0, 0),
                        "angry": (0, 0, 255),
                        "playful": (255, 255, 0),
                        "serious": (200, 200, 200),
                        "default": (180, 180, 180)
                    }.get(self.current_emotion, (180, 180, 180))
                    cv2.putText(img, f"Emotion: {self.current_emotion}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
                    cv2.imshow("A.R.I.S Emotion Monitor", img)
                    cv2.waitKey(500)
                except Exception:
                    # If OpenCV windowing fails (e.g. in headless), fallback to console
                    print(f"\r[Emotion UI] Current emotion: {self.current_emotion}     ", end="")
                time.sleep(3)
        except Exception as e:
            print(f"Emotion UI error: {e}")

    # --------------------------
    # Camera Mode Methods
    # --------------------------
    def start_camera(self):
        if not FACE_RECO_ENABLED:
            self.speak("Face recognition is disabled because the module is missing.")
            return
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.speak("Cannot access the camera.")
            return
        self.speak("Camera started. Press 'c' to capture or 'q' to quit.")
        while True:
            ret, frame = cap.read()
            if not ret:
                self.speak("Failed to grab frame.")
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Real-Time YOLO Object Detection
            if net is not None:
                blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
                net.setInput(blob)
                outputs = net.forward(output_layers)
                for output in outputs:
                    for detection in output:
                        scores = detection[5:]
                        class_id = np.argmax(scores)
                        confidence = scores[class_id]
                        if confidence > 0.5:
                            box = detection[0:4] * np.array([frame.shape[1], frame.shape[0], frame.shape[1], frame.shape[0]])
                            (centerX, centerY, w, h) = box.astype("int")
                            x = int(centerX - (w / 2))
                            y = int(centerY - (h / 2))
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
                            label = classes[class_id] if len(classes) > class_id else str(class_id)
                            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            cv2.imshow("A.R.I.S Camera Mode", frame)
            key = cv2.waitKey(1)
            if key & 0xFF == ord('c'):
                filename = self._save_frame(frame)
                self.speak(f"Photo captured and saved as {filename}")
            elif key & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

    def capture_photo(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.speak("Cannot access the camera.")
            return
        ret, frame = cap.read()
        if ret:
            filename = self._save_frame(frame)
            self.speak(f"Photo captured and saved as {filename}")
        else:
            self.speak("Failed to capture photo.")
        cap.release()
        cv2.destroyAllWindows()

    def _save_frame(self, frame):
        filename = os.path.join(self.temp_dir, f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        cv2.imwrite(filename, frame)
        return filename

    def ocr_last_photo(self, path=None):
        if path is None:
            photos = sorted(glob.glob(os.path.join(self.temp_dir, "photo_*.png")), reverse=True)
            if not photos:
                self.speak("No photos found to perform OCR.")
                return
            path = photos[0]
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        self.speak(f"Extracted text: {text}")
        return text

    def detect_faces_in_photo(self, path=None):
        if not FACE_RECO_ENABLED:
            self.speak("Face recognition is disabled because the module is missing.")
            return
        if path is None:
            photos = sorted(glob.glob(os.path.join(self.temp_dir, "photo_*.png")), reverse=True)
            if not photos:
                self.speak("No photos found for face detection.")
                return
            path = photos[0]
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        self.speak(f"Detected {len(faces)} face(s) in {os.path.basename(path)}")
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
        output_path = os.path.join(self.temp_dir, f"faces_{os.path.basename(path)}")
        cv2.imwrite(output_path, img)
        return output_path

    def detect_objects_in_photo(self, path=None):
        if net is None:
            self.speak("YOLO model not available.")
            return
        if path is None:
            photos = sorted(glob.glob(os.path.join(self.temp_dir, "photo_*.png")), reverse=True)
            if not photos:
                self.speak("No photos found for object detection.")
                return
            path = photos[0]
        image = cv2.imread(path)
        height, width = image.shape[:2]
        blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        layer_outputs = net.forward(output_layers)
        class_ids, confidences, boxes = [], [], []
        for output in layer_outputs:
            for detection in output:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = scores[class_id]
                if confidence > 0.5:
                    box = detection[0:4] * np.array([width, height, width, height])
                    (centerX, centerY, w, h) = box.astype("int")
                    x = int(centerX - (w / 2))
                    y = int(centerY - (h / 2))
                    boxes.append([x, y, int(w), int(h)])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        for i in indices.flatten():
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            # Add class label before drawing rectangle
            if len(classes) > class_ids[i]:
                label = str(classes[class_ids[i]])
            else:
                label = str(class_ids[i])
            cv2.putText(image, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 255), 2)
        output_path = os.path.join(self.temp_dir, f"objects_{os.path.basename(path)}")
        cv2.imwrite(output_path, image)
        self.speak(f"Objects detected and saved to {output_path}")
        return output_path

# --------------------------
# Main Loop
# --------------------------
async def main():
    aris = ARIS()
    # Start watch_folder_loop in background (for shortcut triggers and file summaries)
    asyncio.create_task(aris.watch_folder_loop())
    # Proactively suggest a task based on time of day after ARIS is initialized.
    aris.suggest_proactive_task()
    print("YO BRO - TYPE 'voice' TO START VOICE COMMANDS OR TYPE YOUR COMMANDS BELOW!")
    voice_mode = False
    while True:
        if not voice_mode:
            user_input = input("Enter command (type 'exit' to quit): ").strip()
            if user_input.lower() == "exit":
                aris.emotion_thread_running = False
                cv2.destroyAllWindows()
                aris.speak("Goodbye!")
                break
            elif user_input.lower() == "voice":
                voice_mode = True
                aris.speak("Voice mode activated! Say 'stop voice' to return to text mode.")
            else:
                await aris.parse_command(user_input)
        else:
            result = await aris.listen_and_execute()
            if result == "STOP_VOICE":
                voice_mode = False

if __name__ == "__main__":
    from datetime import timedelta
    asyncio.run(main())