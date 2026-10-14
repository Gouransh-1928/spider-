@echo off
echo ========================================
echo   SPIDER AI System — Installer
echo ========================================
echo.

:: Check Python
python --version 2>NUL
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [2/5] Downloading Whisper STT model...
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

echo.
echo [3/5] Downloading sentence-transformers model...
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

echo.
echo [4/5] Installing Playwright browser...
playwright install chromium

echo.
echo [5/5] Checking Ollama...
ollama --version 2>NUL
if errorlevel 1 (
    echo.
    echo [WARNING] Ollama not found!
    echo Please install Ollama from: https://ollama.ai
    echo Then run: ollama pull llama3.2
    echo.
) else (
    echo Ollama found. Pulling llama3.2 model (this may take a while)...
    ollama pull llama3.2
)

echo.
echo ========================================
echo   SPIDER Installation Complete!
echo ========================================
echo.
echo To start SPIDER: python main.py
echo To register auto-start: python startup\register_startup.py
echo.
pause
