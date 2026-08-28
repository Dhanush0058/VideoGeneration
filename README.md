# StudyFlow AI

StudyFlow AI is an AI-powered educational video generator inspired by **NotebookLM Video Overviews**. It converts uploaded documents (PDF/TXT), raw text notes, or topics into structured, storyboarded educational videos.

The application has a robust **Low-Resource fallback mode** that allows it to generate high-quality educational explainers without requiring an expensive GPU or paid AI model APIs.

---

## Technical Architecture

```
PDF/Text / Topic Input
       ↓
[DocumentProcessor] (fitz / PyMuPDF text isolation & cleanup)
       ↓
[LLMService] (Structured JSON script layout with Pydantic validation)
       ↓
[ScenePlanner] (Decides storyboard animations, visuals, transitions)
       ↓
 ┌─────────────────────────┼─────────────────────────┐
 ↓                         ↓                         ↓
[ImageService]            [TTSService]             [OptionalVideoService]
 - HF Inference API        - Edge-TTS (Default Free)  - LTX-Video / Wan
 - PIL Infographic Slides  - Offline pyttsx3 fallback - Ken Burns Zoom Filters
       ↓                         ↓                         ↓
 └─────────────────────────┼─────────────────────────┘
                           ↓
                     [VideoRenderer] (Compile individual scene MP4s)
                           ↓
                     [FFmpeg Concatenator] (Stitch scene clips together)
                           ↓
                   [Final Output MP4] (Downloadable with burned Subtitles)
```

---

## Project Structure

```
VideoGenerationAI/
├── backend/
│   ├── main.py                 # FastAPI Web Server Entrypoint
│   ├── config.py               # Env Configuration loader (Pydantic Settings)
│   ├── api/                    # API Routing controllers
│   │   ├── upload.py           # POST /api/upload
│   │   ├── generation.py       # POST /api/analyze & /api/generate-script
│   │   └── video.py            # POST /api/video/generate-video, GET /status, /download
│   ├── services/               # Core business services
│   │   ├── document_service.py # PDF Text Extraction
│   │   ├── llm_service.py      # LLM API & Mock Orchestration
│   │   ├── image_service.py    # HF API & Programmatic Slide Generator
│   │   ├── tts_service.py      # Edge-TTS & offline audio generation
│   │   └── subtitle_service.py # WebVTT subtitle track compiling
│   ├── models/                 # Pydantic Schemas
│   │   ├── scene.py
│   │   ├── script.py
│   │   └── job.py
│   ├── video/                  # FFmpeg clip compilers
│   │   └── renderer.py
│   └── requirements.txt        # Python package requirements
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main React Application UI (Pages, Editor)
│   │   ├── index.css           # Global stylesheet & Tailwind configurations
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json            # Vite npm dependencies
│   ├── postcss.config.js
│   └── tailwind.config.js      # Tailwind Styling themes
└── README.md
```

---

## 🛠️ Installation & Setup Instructions

### 1. Prerequisites (FFmpeg Installation)
StudyFlow AI relies on **FFmpeg** to animate scenes, merge audio streams, and stitch the final video.

- **Windows**:
  1. Download FFmpeg from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
  2. Extract the folder to a safe place (e.g., `C:\ffmpeg`).
  3. Add the `bin` directory (e.g., `C:\ffmpeg\bin`) to your Windows System PATH environment variable.
- **Mac**:
  ```bash
  brew install ffmpeg
  ```
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install ffmpeg -y
  ```

---

### 2. Backend Setup
1. Open a terminal and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Prepare your `.env` configuration. A default `.env` has already been generated to allow **zero-key, zero-cost mock execution** out-of-the-box.
4. Run the FastAPI development server:
   ```bash
   python -m backend.main
   ```
   *The backend will boot on [http://127.0.0.1:8000](http://127.0.0.1:8000).*

---

### 3. Frontend Setup
1. Open a second terminal and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Boot the Vite development server:
   ```bash
   npm run dev
   ```
   *The user interface will load at [http://localhost:5173](http://localhost:5173).*

---

## 🔑 External API Key Integrations (Optional)

To enable advanced AI content generation instead of the default free fallback engines, fill in the fields in `backend/.env`:

### A. Text / Script Generation (`LLM_PROVIDER`)
- Set `LLM_PROVIDER=GEMINI` and supply a `GEMINI_API_KEY` (Free tier available).
- Set `LLM_PROVIDER=GROQ` and supply a `GROQ_API_KEY` (Highly recommended: ultra-fast Llama-3 text completion, free tier).
- Set `LLM_PROVIDER=OPENAI` and supply an `OPENAI_API_KEY`.

### B. Slide Visual Generation (`IMAGE_PROVIDER`)
- Set `IMAGE_PROVIDER=HF_API` and supply a `HF_TOKEN` (Hugging Face serverless inference token, which is free) to generate images from prompts using models like stable-diffusion-xl or Flux.1.
- Leave `IMAGE_PROVIDER=DIAGRAM_FALLBACK` to programmatically build beautiful diagram layouts with custom card blocks, icons, and arrows (default, offline-friendly, fast rendering).

### C. Narration Voice (`TTS_PROVIDER`)
- Set `TTS_PROVIDER=EDGE_TTS` (Default, uses Microsoft Edge's free narration API. Yields high quality human-like voices like `en-US-GuyNeural` without keys).
- Set `TTS_PROVIDER=LOCAL_PYTTSX3` to run fully offline using your computer's built-in text-to-speech engine.

---

## ⚡ Running Your First Generation (Demo)

1. Open [http://localhost:5173](http://localhost:5173) in your browser.
2. Click **Try Example** on the landing page.
3. Review the populated parameters (topic: "Explain the OSI Model", settings: "Notebook" style).
4. Click **Generate Video**.
5. Watch the pipeline advance through the stages in real-time. Since it compiles in demonstration mode, it will render rapidly.
6. Play the completed video in the custom player, toggle subtitles on, download the `.mp4` file, or select individual scenes in the **Storyboard Timeline** to test single-scene updating in the editor.
