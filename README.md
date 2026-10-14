 HEAD
# 🕷️ SPIDER — Personal AI Assistant

**SPIDER** is a fully offline, voice-activated AI personal assistant built in Python. It's yours — no cloud, no subscriptions, no data leaving your machine.

## Features

| Feature | Description |
|---------|-------------|
|  Voice Control | Wake word "Hey SPIDER" + voice passkey security |
|  AI Brain | Local LLM via Ollama (Llama 3, Mistral, etc.) |
|  Memory | ChromaDB persistent memory across sessions |
|  File Manager | Create, delete, rename, copy, move, open files/folders |
| System Control | Volume, brightness, screenshots, lock, shutdown |
|  Web Search | Jobs, shopping, general search via DuckDuckGo |
|  Code Writer | Generate code, run it, auto-retry if it fails |
|  Resume Updater | Search jobs → extract skills → update your .docx |
|  Phone Control | Unlock, open apps, YouTube, calls, SMS via ADB |
| 🇮🇳 Multilingual | Hindi, English, Hinglish — SPIDER replies naturally |

---

## Quick Start

### Prerequisites

1. **Python 3.11+** — [Download](https://www.python.org/downloads/)
2. **Ollama** — [Download](https://ollama.ai) — Run in terminal: `ollama pull llama3.1`
3. **ADB** (for phone control) — [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)

### Installation

```bash
# 1. Clone / open the SPIDER folder
cd path\to\SPIDER

# 2. Run the installer (installs everything)
install.bat

# 3. Test everything works
python tests\test_spider.py

# 4. Start SPIDER!
python main.py
```

### First Run

On first run, SPIDER will:
1. Ask if you want to activate
2. Walk you through **voice passkey enrollment** (say your secret phrase 3 times)
3. Start listening for your commands!

---

## Phone Setup (One-time)

1. On your Android phone: **Settings → About Phone → Tap Build Number 7 times**
2. **Settings → Developer Options → Enable USB Debugging**
3. Connect phone via USB
4. Tap **"Allow"** when prompted on the phone
5. Tell SPIDER: *"Connect to my phone"*

---

## Example Commands

```
"Hey SPIDER"                              → Wake up
"SPIDER, create a folder called Projects on my Desktop"
"SPIDER, write Python code for a to-do list app"
"SPIDER, search for Python developer jobs"
"SPIDER, update my resume for a data analyst job"
"SPIDER, unlock my phone"
"SPIDER, open WhatsApp on my phone"
"SPIDER, play Bollywood songs on YouTube"
"SPIDER, take a screenshot"
"SPIDER, volume up"
"SPIDER, what is the weather in Delhi?"
```

---

## Auto-Start on Login

```bash
# Run once as Administrator
python startup\register_startup.py
```

---

## Configuration

Edit `config/settings.yaml` to change:
- LLM model (`brain.model`) — try `mistral`, `codellama`, `phi3`
- Wake word phrase
- TTS voice
- Resume path
- ADB device

---

## Project Structure

```
SPIDER/
├── main.py                 ← Start here
├── install.bat             ← One-click installer
├── requirements.txt
├── config/
│   ├── settings.yaml       ← All settings
│   └── loader.py
├── core/
│   ├── brain.py            ← Ollama LLM + skill dispatch
│   ├── memory.py           ← ChromaDB long-term memory
│   └── context.py          ← Short-term conversation
├── voice/
│   ├── speaker.py          ← TTS (edge-tts, female voice)
│   ├── listener.py         ← STT (faster-whisper, multilingual)
│   ├── wake_word.py        ← "Hey SPIDER" detection
│   └── language.py         ← Hindi/English/Hinglish detection
├── skills/
│   ├── file_manager.py     ← File operations
│   ├── app_launcher.py     ← Open/close apps
│   ├── system_control.py   ← Volume, brightness, etc.
│   ├── web_search.py       ← DuckDuckGo + scraping
│   ├── code_writer.py      ← AI code generation + retry
│   └── resume_updater.py   ← Job search + .docx update
├── phone/
│   ├── adb_bridge.py       ← ADB commands
│   └── phone_skills.py     ← NL → phone actions
├── security/
│   └── auth.py             ← Voice passkey (Resemblyzer)
├── startup/
│   ├── boot_listener.py    ← Startup flow
│   └── register_startup.py ← Windows Task Scheduler
├── data/
│   ├── memory/             ← ChromaDB store
│   ├── resumes/            ← Your resume files
│   └── logs/               ← Logs
└── tests/
    └── test_spider.py      ← System test
```
=======
# spider-
voice controlled AI assistant build with python that has access to all my pc and my phone , it also has a security pass key before initial start of the whole program . this program can write codes for me, do web search and much more.
f924d56cf7746a0725677060478aaf64e420911a
