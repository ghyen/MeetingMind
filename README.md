# MeetingMind

Local-first AI meeting assistant for real-time transcript, topic detection, issue structuring, reference search, and intervention triggers.

MeetingMind combines STT, speaker identification, LLM analysis, and a browser UI into one FastAPI pipeline. It is built for meetings where privacy and low-latency feedback matter, so the core analysis can run against local LLM backends without sending meeting audio to an external API.

## Features

- Real-time microphone streaming over WebSocket
- File upload transcription for recorded meetings
- Whisper-based Korean STT with VAD and repetition filtering
- Speaker identification with 3D-Speaker / sherpa-onnx models
- Automatic topic detection and issue structuring
- Intervention triggers for loops, long silence, time overrun, and consensus checks
- Reference collection with local vector search and optional Tavily web search
- Meeting history and summaries stored in SQLite
- Browser UI for live transcript, issues, interventions, references, and server logs

## Demo

- Demo video: https://drive.google.com/file/d/1-uzp9wPoEWWO8sxKYutJPBD9GScMuWh0/view?usp=sharing

## Tech Stack

- Backend: FastAPI, WebSocket, asyncio, Pydantic
- STT: faster-whisper / mlx-whisper, Silero VAD
- Speaker diarization: 3D-Speaker, sherpa-onnx
- LLM: Ollama, llama.cpp-compatible OpenAI endpoint, OpenRouter
- Search / RAG: ChromaDB, Tavily
- Database: SQLite, aiosqlite
- Frontend: React-style browser UI served from `static/`

## Architecture

```text
microphone / audio file / text simulation
        |
        v
STT + speaker identification
        |
        v
Pipeline.on_utterance()
        |
        +-- topic detection
        +-- issue structuring
        +-- intervention triggers
        +-- reference search
        +-- SQLite persistence
        |
        v
WebSocket updates + browser UI
```

Main flow:

1. `main.py` starts FastAPI and initializes SQLite.
2. `api/websocket.py` receives live audio chunks through `/ws/audio`.
3. `stt/whisper_stt.py` converts audio into `Utterance` objects.
4. `pipeline.py` routes each utterance through analysis modules.
5. `analysis/` detects topics, issues, summaries, corrections, and triggers.
6. `search/` collects references when issues need supporting material.
7. `static/` renders the live meeting interface.

More detail: see `docs/FLOW.md`.

## Quick Start

```bash
git clone https://github.com/ghyen/MeetingMind.git
cd MeetingMind

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn main:app --reload
```

Open:

```text
http://localhost:8000/static/index.html
```

## Configuration

All runtime settings use the `MM_` prefix and can be changed in `.env`.

Common settings:

```bash
MM_LLM_PROVIDER=bonsai
MM_BONSAI_BASE_URL=http://localhost:8080/v1
MM_BONSAI_MODEL=gemma4-e2b-mlx
MM_OLLAMA_BASE_URL=http://localhost:11434/v1
MM_TAVILY_API_KEY=
MM_DB_PATH=data/meetingmind.db
MM_CHROMADB_PATH=data/chromadb
MM_HOST=0.0.0.0
MM_PORT=8000
MM_STT_LANGUAGE=ko
MM_STT_MODEL_SIZE=large-v3-turbo
MM_DIARIZATION_ENABLED=true
```

LLM provider options:

- `bonsai`: OpenAI-compatible local endpoint such as llama.cpp
- `ollama`: local Ollama endpoint
- `openrouter`: hosted model through OpenRouter API key

## API

Meeting lifecycle:

```http
POST /api/meeting/start
POST /api/meeting/end
GET  /api/meeting/state
PUT  /api/meeting/title
```

Input:

```http
POST /api/meeting/upload
POST /api/meeting/simulate
WS   /ws/audio
WS   /ws/speaker
```

Topic and history:

```http
GET  /api/meeting/topics
POST /api/meeting/topics
PUT  /api/meeting/topics/{topic_id}
```

## Development Notes

- `POST /api/meeting/simulate` is useful when testing the analysis pipeline without audio.
- `scripts/generate_meeting_audio.py` and `scripts/run_audio_test.py` are useful for repeatable audio tests.
- `docs/PAPERS.md` contains related research notes for ASR, diarization, meeting summarization, and intervention design.
- `.env.example` documents the main tunable thresholds for STT, topic detection, issue batching, and intervention triggers.

## Project Structure

```text
MeetingMind/
|-- main.py                 # FastAPI entrypoint
|-- pipeline.py             # utterance orchestration
|-- api/                    # REST and WebSocket routes
|-- analysis/               # topic, issue, trigger, summary, correction logic
|-- stt/                    # Whisper STT and speaker identification
|-- search/                 # reference collection and vector/web search
|-- db/                     # SQLite persistence
|-- static/                 # browser UI
|-- scripts/                # test, benchmark, indexing, presentation helpers
`-- docs/                   # flow and research notes
```

## Results Highlight

- End-to-end live analysis target: under 2 seconds for interaction feedback
- Resolved repeated Whisper hallucination loops with layered diagnostics
- Reduced unnecessary LLM calls through token-threshold-based issue batching
- Supports local-first operation for meeting privacy

## License

No license file has been added yet.
