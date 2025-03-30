import os
import datetime
import subprocess
import webbrowser
import pyautogui
import requests
import logging
from flask import Flask, request, jsonify, render_template
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from gtts import gTTS
from pygame import mixer
import tempfile

import time

from flask import Flask, render_template, url_for

# Initialize Flask with static file configuration
app = Flask(__name__,
            static_folder='static',  # Path to static files
            static_url_path='')      # URL prefix for static files


# Configuration
PASSCODE = "हेलो"
LANGUAGE = "hindi"
GEMINI_API_KEY = "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"
MODEL_NAME = "google/gemini-2.5-pro-exp-03-25:free"
TTS_VOICE = {
    "hindi": {"lang": "hi", "gender": "female"},
    "english": {"lang": "en", "gender": "female"}
}

# Initialize pygame mixer
mixer.init()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

responses = {
    "hindi": {
        "welcome": "नमस्ते! मैं आपकी कैसे मदद कर सकती हूँ?",
        "passcode_prompt": "कृपया अपना पासकोड बताइए",
        "passcode_accepted": "पासकोड स्वीकार किया गया! आपका स्वागत है!",
        "passcode_incorrect": "गलत पासकोड। आपके पास {attempts} और प्रयास बाकी हैं।",
        "passcode_failed": "बहुत अधिक गलत प्रयास। मैं बंद हो रही हूँ।",
        "not_found": "मुझे समझ नहीं आया। कृपया फिर से बोलिए।",
        "goodbye": "अलविदा! आपका दिन शुभ रहे।",
        "time": lambda: f"अभी समय हुआ है {datetime.datetime.now().strftime('%H:%M')}",
        "date": lambda: f"आज की तारीख है {datetime.datetime.now().strftime('%Y-%m-%d')}",
        "search_prompt": "आप क्या खोजना चाहेंगी?",
        "searching": "मैं '{query}' के बारे में जानकारी ढूंढ रही हूँ",
        "notepad_open": "मैंने नोटपैड खोल दिया है",
        "notepad_close": "मैंने नोटपैड बंद कर दिया है",
        "browser_open": "मैंने ब्राउज़र खोल दिया है",
        "browser_close": "मैंने ब्राउज़र बंद कर दिया है",
        "youtube_open": "मैंने यूट्यूब खोल दिया है",
        "song_prompt": "आप कौन सा गाना सुनना चाहेंगी?",
        "playing_song": "मैं YouTube पर '{song}' चला रही हूँ",
        "media_play": "मैं मीडिया चला रही हूँ",
        "media_pause": "मैंने मीडिया रोक दिया है",
        "volume_set": "मैंने वॉल्यूम {level} प्रतिशत पर सेट कर दिया है",
        "screenshot": "मैंने स्क्रीनशॉट ले लिया है और सेव कर दिया है",
        "error": "माफ कीजिए, कुछ गड़बड़ हुई है। कृपया फिर से कोशिश करें",
        "ai_activate": "जेमिनी प्रो मोड चालू हुआ। कृपया अपना प्रश्न बोलिए।",
        "ai_thinking": "मैं सोच रही हूँ...",
        "ai_error": "मैं इस समय जवाब नहीं दे पा रही हूँ। कृपया थोड़ी देर बाद कोशिश करें।",
        "listening": "सुन रही हूँ...",
        "mic_error": "माइक्रोफ़ोन एक्सेस में समस्या आई है",
        "ai_question_prompt": "अब आप अपना प्रश्न पूछ सकते हैं"
    },
    "english": {
        "welcome": "Hello! How may I help you today?",
        "passcode_prompt": "Please tell me the passcode",
        "passcode_accepted": "Passcode accepted! Welcome!",
        "passcode_incorrect": "Wrong passcode. You have {attempts} attempts left.",
        "passcode_failed": "Too many wrong attempts. I'm shutting down.",
        "not_found": "I didn't understand that. Could you please repeat?",
        "goodbye": "Goodbye! Have a wonderful day.",
        "time": lambda: f"The current time is {datetime.datetime.now().strftime('%H:%M')}",
        "date": lambda: f"Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}",
        "search_prompt": "What would you like me to search for?",
        "searching": "I'm looking up information about '{query}'",
        "notepad_open": "I've opened Notepad for you",
        "notepad_close": "I've closed Notepad",
        "browser_open": "I've opened the browser",
        "browser_close": "I've closed the browser",
        "youtube_open": "I've opened YouTube",
        "song_prompt": "Which song would you like me to play?",
        "playing_song": "Playing '{song}' on YouTube",
        "media_play": "I'm playing the media now",
        "media_pause": "I've paused the media",
        "volume_set": "I've set the volume to {level} percent",
        "screenshot": "I've taken a screenshot and saved it",
        "error": "I'm sorry, something went wrong. Please try again.",
        "ai_activate": "Gemini Pro mode activated. Please ask your question now.",
        "ai_thinking": "Let me think about that...",
        "ai_error": "I'm having trouble responding right now. Please try again later.",
        "listening": "Listening...",
        "mic_error": "Microphone access error",
        "ai_question_prompt": "You may now ask your question"
    }
}

def speak(text):
    """Function to make the assistant speak using Google TTS with proper cleanup"""
    try:
        lang = TTS_VOICE[LANGUAGE]["lang"]
        tts = gTTS(text=text, lang=lang, slow=False)
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
            temp_file = fp.name
            tts.save(temp_file)
        
        mixer.music.load(temp_file)
        mixer.music.play()
        
        # Wait for playback to finish
        while mixer.music.get_busy():
            time.sleep(0.1)
            
        os.remove(temp_file)
        
    except Exception as e:
        logger.error(f"TTS Error: {str(e)}")
        print(f"TTS Error: {e}")

def get_template_commands():
    """Generate example commands for the template"""
    return {
        "time": responses[LANGUAGE]['time'](),
        "date": responses[LANGUAGE]['date'](),
        "notepad": responses[LANGUAGE]['notepad_open'],
        "browser": responses[LANGUAGE]['browser_open'],
        "youtube": responses[LANGUAGE]['youtube_open'],
        "gemini": responses[LANGUAGE]['ai_activate'],
        "screenshot": responses[LANGUAGE]['screenshot'],
        "goodbye": responses[LANGUAGE]['goodbye']
    }

@app.route('/ask_gemini', methods=['POST'])
def handle_gemini_question():
    """Endpoint to process Gemini AI questions with full error handling"""
    data = request.get_json()
    question = data.get('question', '').strip()
    
    if not question:
        error_msg = responses[LANGUAGE]['not_found']
        speak(error_msg)
        return jsonify({
            "text": error_msg,
            "status": "error",
            "current_language": LANGUAGE
        })
    
    try:
        # Acknowledge question receipt
        speak(responses[LANGUAGE]['ai_thinking'])
        
        # Process the question
        result = ask_ai(question)
        result['current_language'] = LANGUAGE
        
        if result['status'] == "success":
            speak(result['text'])
        else:
            speak(responses[LANGUAGE]['ai_error'])
            
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Question handling error: {str(e)}")
        error_msg = responses[LANGUAGE]['ai_error']
        speak(error_msg)
        return jsonify({
            "text": error_msg,
            "status": "error",
            "current_language": LANGUAGE
        })

def ask_ai(question):
    """Enhanced Gemini AI query function with timeout and retry"""
    try:
        headers = {
            "Authorization": f"Bearer {GEMINI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": question}],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return {
                "text": response.json()["choices"][0]["message"]["content"],
                "status": "success"
            }
        else:
            error_msg = f"API Error {response.status_code}: {response.text}"
            logger.error(error_msg)
            return {
                "text": responses[LANGUAGE]['ai_error'],
                "status": "error"
            }
            
    except requests.exceptions.Timeout:
        logger.error("Gemini API timeout")
        return {
            "text": responses[LANGUAGE]['ai_error'],
            "status": "error"
        }
    except Exception as e:
        logger.error(f"AI Connection Error: {str(e)}")
        return {
            "text": responses[LANGUAGE]['ai_error'],
            "status": "error"
        }

def open_notepad():
    """Open Notepad with error handling"""
    try:
        subprocess.Popen(["notepad.exe"])
        return {
            "text": responses[LANGUAGE]['notepad_open'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Notepad error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def close_notepad():
    """Close Notepad with error handling"""
    try:
        os.system("taskkill /f /im notepad.exe")
        return {
            "text": responses[LANGUAGE]['notepad_close'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Close Notepad error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def open_browser():
    """Open default browser with error handling"""
    try:
        webbrowser.open("https://www.google.com")
        return {
            "text": responses[LANGUAGE]['browser_open'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Browser error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def close_browser():
    """Close common browsers with error handling"""
    try:
        os.system("taskkill /im chrome.exe /f & taskkill /im msedge.exe /f & taskkill /im firefox.exe /f")
        return {
            "text": responses[LANGUAGE]['browser_close'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Close browser error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def open_youtube():
    """Open YouTube with error handling"""
    try:
        webbrowser.open("https://www.youtube.com")
        return {
            "text": responses[LANGUAGE]['youtube_open'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Youtube error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def play_youtube_song(query):
    """Play YouTube song with error handling"""
    try:
        song = query.replace("play", "").replace("गाना चलाओ", "").strip()
        if not song:
            return {
                "text": responses[LANGUAGE]['song_prompt'],
                "action": "search_youtube_song",
                "status": "success",
                "current_language": LANGUAGE
            }
            
        webbrowser.open(f"https://www.youtube.com/results?search_query={song}")
        return {
            "text": responses[LANGUAGE]['playing_song'].format(song=song),
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Play song error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def play_media():
    """Play media with error handling"""
    try:
        pyautogui.press('playpause')
        return {
            "text": responses[LANGUAGE]['media_play'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Media play error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def pause_media():
    """Pause media with error handling"""
    try:
        pyautogui.press('playpause')
        return {
            "text": responses[LANGUAGE]['media_pause'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Media pause error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def toggle_fullscreen():
    """Toggle fullscreen with error handling"""
    try:
        pyautogui.press('f')
        return {
            "text": "Fullscreen toggled",
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Fullscreen error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def set_volume(level):
    """Set system volume with error handling"""
    try:
        level = max(0, min(int(level), 100))
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        return {
            "text": responses[LANGUAGE]['volume_set'].format(level=level),
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Volume error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def take_screenshot():
    """Take screenshot with error handling"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        pyautogui.screenshot(filename)
        return {
            "text": responses[LANGUAGE]['screenshot'],
            "status": "success",
            "current_language": LANGUAGE
        }
    except Exception as e:
        logger.error(f"Screenshot error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "status": "error",
            "current_language": LANGUAGE
        }

def change_language():
    """Change language with full synchronization"""
    global LANGUAGE
    try:
        LANGUAGE = "hindi" if LANGUAGE == "english" else "english"
        return {
            "text": responses[LANGUAGE]['welcome'],
            "current_language": LANGUAGE,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Language change error: {str(e)}")
        return {
            "text": responses[LANGUAGE]['error'],
            "current_language": LANGUAGE,
            "status": "error"
        }

def process_audio_command(text):
    """Main command processor with enhanced error handling"""
    try:
        text_lower = text.lower()
        
        if any(greeting in text_lower for greeting in ["hello", "hi", "नमस्ते", "हेलो"]):
            return {
                "text": responses[LANGUAGE]['welcome'],
                "current_language": LANGUAGE,
                "status": "success"
            }
        
        elif "time" in text_lower or "समय" in text_lower:
            return {
                "text": responses[LANGUAGE]['time'](),
                "current_language": LANGUAGE,
                "status": "success"
            }
        
        elif "date" in text_lower or "तारीख" in text_lower:
            return {
                "text": responses[LANGUAGE]['date'](),
                "current_language": LANGUAGE,
                "status": "success"
            }
        
        elif "नोटपैड खोलो" in text_lower or ("notepad" in text_lower and "open" in text_lower):
            return open_notepad()
        
        elif "नोटपैड बंद करो" in text_lower or ("notepad" in text_lower and "close" in text_lower):
            return close_notepad()
        
        elif "ब्राउज़र खोलो" in text_lower or ("browser" in text_lower and "open" in text_lower):
            return open_browser()
        
        elif "ब्राउज़र बंद करो" in text_lower or ("browser" in text_lower and "close" in text_lower):
            return close_browser()
        
        elif "यूट्यूब खोलो" in text_lower or "youtube" in text_lower:
            return open_youtube()
        
        elif "गाना चलाओ" in text_lower or "संगीत चलाओ" in text_lower or "play song" in text_lower or "play music" in text_lower:
            return play_youtube_song(text_lower)
        
        elif "चलाओ" in text_lower or "play" in text_lower:
            return play_media()
        
        elif "रोको" in text_lower or "pause" in text_lower or "stop" in text_lower:
            return pause_media()
        
        elif "पूर्ण स्क्रीन" in text_lower or "full screen" in text_lower:
            return toggle_fullscreen()
        
        elif "आवाज" in text_lower or "volume" in text_lower:
            try:
                level = int(''.join(filter(str.isdigit, text_lower)))
                return set_volume(level)
            except ValueError:
                speak(responses[LANGUAGE]['error'])
                return {
                    "text": responses[LANGUAGE]['error'],
                    "current_language": LANGUAGE,
                    "status": "error"
                }
        
        elif "स्क्रीनशॉट" in text_lower or "screenshot" in text_lower:
            return take_screenshot()
        
        elif "भाषा बदलो" in text_lower or "change language" in text_lower:
            return change_language()
        
        elif "ask gemini" in text_lower or "जेमिनी से पूछो" in text_lower:
            return {
                "text": responses[LANGUAGE]['ai_activate'],
                "action": "activate_gemini",
                "follow_up": True,
                "current_language": LANGUAGE,
                "status": "success"
            }
        
        elif "बंद करो" in text_lower or "अलविदा" in text_lower or "exit" in text_lower or "quit" in text_lower or "goodbye" in text_lower:
            return {
                "text": responses[LANGUAGE]['goodbye'],
                "action": "exit",
                "current_language": LANGUAGE,
                "status": "success"
            }
        
        else:
            return {
                "text": responses[LANGUAGE]['not_found'],
                "current_language": LANGUAGE,
                "status": "error"
            }
            
    except Exception as e:
        logger.error(f"Command processing error: {str(e)}")
        speak(responses[LANGUAGE]['error'])
        return {
            "text": responses[LANGUAGE]['error'],
            "current_language": LANGUAGE,
            "status": "error"
        }

@app.route('/process_command', methods=['POST'])
def handle_command():
    """Main command endpoint with full error handling"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            raise ValueError("Invalid request format")
            
        command = data.get('command', '').strip()
        if not command:
            raise ValueError("Empty command")
        
        result = process_audio_command(command)
        
        # Speak the initial response if available
        if 'text' in result:
            speak(result['text'])
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Endpoint error: {str(e)}")
        error_msg = responses[LANGUAGE]['error']
        speak(error_msg)
        return jsonify({
            "text": error_msg,
            "current_language": LANGUAGE,
            "status": "error"
        })

@app.route('/get_current_language', methods=['GET'])
def get_current_language():
    return jsonify({
        "language": LANGUAGE,
        "display_name": "Hindi" if LANGUAGE == "hindi" else "English"
    })

#@app.route('/')
#def index():
#    return render_template(
#        'index.html',
#        responses=responses[LANGUAGE],
#        commands=get_template_commands(),
#        LANGUAGE=LANGUAGE
#    )

@app.route('/')
def index():
    return render_template('index.html',
                         responses=responses[LANGUAGE],
                         commands=get_template_commands(),
                         LANGUAGE=LANGUAGE)
    
@app.route('/test-static')
def test_static():
    return f"""
    <h1>Static File Test</h1>
    <p>CSS path: {url_for('static', filename='css/styles.css')}</p>
    <p>Sample image test: <img src="{url_for('static', filename='images/test.png')}" alt="Test"></p>
    """

if __name__ == '__main__':
    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(os.getcwd(), "tts_temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Run the app with explicit host and port
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)