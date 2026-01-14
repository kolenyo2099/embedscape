# EmbedScape v2.0

Semantic embedding visualization with Python backend and Svelte frontend.

## Architecture

```
┌─────────────────────────────────────────────┬─────────────────┐
│                                             │                 │
│           MAIN PANEL                        │   RIGHT PANEL   │
│        (Graph Visualization)                │  (Code Editor)  │
│         deck.gl + OrthographicView          │     Monaco      │
│                                             │                 │
├─────────────────────────────────────────────┴─────────────────┤
│                     BOTTOM PANEL                              │
│                   (Data Preview Table)                        │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start

### Easy Way (Recommended)

```bash
# Just run the start script - it handles everything!
./start.sh
```

**First run**: Creates uv environment, installs all dependencies, starts both servers
**Subsequent runs**: Just starts both servers

Press `Ctrl+C` to stop both servers.

### Manual Way

#### Backend (Python)

```bash
cd backend

# With uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py

# Or with standard Python
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python main.py
```

#### Frontend (Svelte)

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:5173 in your browser.

## Features

### Data Loading
- CSV and NDJSON file upload
- Direct image/video upload
- Session save/load
- Social media data flattening (Twitter, Instagram, TikTok)

### Embedding Pipeline
- **Text**: all-MiniLM-L6-v2 via sentence-transformers
- **Multimodal**: CLIP ViT-B/32 for text/image/video
- Video frame extraction with configurable FPS
- Parallel processing with progress updates via WebSocket

### Visualization
- Interactive 2D scatter plot (deck.gl with OrthographicView)
- Pan, zoom, and click interactions
- Color by cluster or by tag
- Highlighted search results

### Semantic Search
- Text query search
- Image query search (multimodal mode)
- Adjustable similarity threshold
- Click results to zoom

### Tagging System
- Single/multi-select modes
- Add/remove custom tags
- Filter visualization by tags
- Tags saved with sessions

### Code Editor
- Monaco editor integration
- Python and SQL support
- Data transformation (planned)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/data/upload` | Upload CSV/NDJSON |
| POST | `/api/data/upload/media` | Upload images/videos |
| GET | `/api/data/preview` | Get data preview |
| POST | `/api/embeddings/generate` | Start embedding job |
| GET | `/api/embeddings/result` | Get embeddings |
| POST | `/api/search/text` | Text search |
| POST | `/api/search/image` | Image search |
| POST | `/api/sessions/save` | Save session |
| POST | `/api/sessions/load` | Load session |
| WS | `/ws/progress` | Real-time progress |

## Tech Stack

### Backend
- FastAPI
- sentence-transformers
- transformers (CLIP)
- scikit-learn (k-means)
- umap-learn
- OpenCV (video processing)

### Frontend
- SvelteKit
- deck.gl (OrthographicView - 2D scatter, NOT map)
- Monaco Editor
- TypeScript

## Project Structure

```
embedscape/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── api/
│   │   ├── routes/
│   │   │   ├── data.py
│   │   │   ├── embeddings.py
│   │   │   ├── search.py
│   │   │   └── sessions.py
│   │   └── websocket.py
│   ├── services/
│   │   ├── embedder.py
│   │   ├── clustering.py
│   │   ├── parser.py
│   │   └── video_processor.py
│   └── models/
│       └── schemas.py
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── MainPanel/Graph.svelte
│   │   │   │   ├── BottomPanel/DataPreview.svelte
│   │   │   │   ├── RightPanel/CodeEditor.svelte
│   │   │   │   └── Sidebar/...
│   │   │   ├── stores/
│   │   │   │   ├── data.ts
│   │   │   │   └── ui.ts
│   │   │   └── api/client.ts
│   │   └── routes/+page.svelte
│   └── package.json
└── README.md
```

## Start Script Features

The `start.sh` script provides:

- ✅ **Auto-installation**: Installs `uv` if not present
- ✅ **First-run setup**: Creates virtual environment and installs all dependencies
- ✅ **Parallel execution**: Runs both backend and frontend simultaneously
- ✅ **Clean shutdown**: Stops both servers with `Ctrl+C`
- ✅ **Status indicators**: Colored output shows what's happening
- ✅ **Smart detection**: Only installs dependencies if needed

### What the script does:

1. **First Run**:
   - Installs `uv` (if needed)
   - Creates Python virtual environment with `uv venv`
   - Installs Python dependencies with `uv pip install`
   - Installs Node.js dependencies with `npm install`
   - Starts both servers

2. **Subsequent Runs**:
   - Detects existing environments
   - Directly starts both servers

### URLs:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

