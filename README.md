# Agentic RAG Research Assistant

This project combines a Next.js frontend with a FastAPI backend for grounded research and study-material retrieval.

## Project Layout

- `frontend/` contains the Next.js UI, components, public assets, and Node.js dependencies.
- `backend/` contains the FastAPI service, agent loop, ingestion pipeline, retrieval stack, pgvector store, and Python dependencies.
- `docker-compose.yml` runs the frontend, backend, and PostgreSQL/pgvector database together.

The backend supports PDF, DOCX, PPTX, TeX, and TXT ingestion, hybrid pgvector plus BM25 retrieval, live arXiv/web lookup, and citation verification before responses stream to the UI.

## Local Development

Create the Python environment and install both dependency sets:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd frontend
npm install
```

Run the backend from the repository root:

```powershell
cd backend
uvicorn api.main:app --reload --port 8000
```

Run the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

The frontend is available at `http://localhost:3000`; the API documentation is available at `http://localhost:8000/docs`.

## Docker Compose

Set `GROQ_API_KEY` in the environment, then run:

```powershell
docker compose up --build
```

This starts PostgreSQL with pgvector on port `5432`, the API on port `8000`, and the frontend on port `3000`.
