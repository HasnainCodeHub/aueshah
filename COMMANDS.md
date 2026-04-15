# Backend Commands Reference

All commands assume working directory `backend/` unless noted. The project uses **uv** (not pip) for Python dependency management.

---

## 1. Environment Setup

### One-time install
```bash
cd backend
uv sync                       # install runtime + dev dependencies from uv.lock
uv sync --no-dev              # install runtime dependencies only (production)
```

### Update lockfile after editing `pyproject.toml`
```bash
uv lock                       # regenerate uv.lock
uv sync                       # apply the new lockfile
```

### Add / remove dependencies
```bash
uv add <package>              # add runtime dep (updates pyproject + lockfile)
uv add --dev <package>        # add dev dep
uv remove <package>           # remove dep
```

### Inspect environment
```bash
uv pip list                   # list installed packages
uv pip show <package>         # show package metadata
uv tree                       # dependency tree
uv python list                # available Python versions
```

---

## 2. Running the Server

### Development (auto-reload)
```bash
uv run uvicorn app.main:app --reload --port 8000
```

### Production-style (no reload, multiple workers)
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Bind to all interfaces (LAN access)
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Endpoints to verify
- Health: `GET http://localhost:8000/health`
- Chat: `POST http://localhost:8000/chat`
- OpenAPI docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3. Testing

### Run all tests
```bash
uv run pytest
```

### Integration tests only
```bash
uv run pytest tests/integration/ -v
```

### Single test file / function
```bash
uv run pytest tests/integration/test_api_endpoint.py -v
uv run pytest tests/integration/test_api_endpoint.py::test_chat_happy_path -v
```

### Useful flags
```bash
uv run pytest -v              # verbose
uv run pytest -x              # stop on first failure
uv run pytest -k "chat"       # filter by name
uv run pytest --tb=short      # short tracebacks
uv run pytest -s              # show print/log output
uv run pytest --lf            # rerun last failed
```

### Coverage (if `pytest-cov` added)
```bash
uv add --dev pytest-cov
uv run pytest --cov=app --cov-report=term-missing
```

---

## 4. Manual API Calls (smoke testing)

### Health check
```bash
curl http://localhost:8000/health
```

### Chat — minimal
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about the Noor collection"}'
```

### Chat — with conversation context
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which would suit a warm skin tone?",
    "context": [
      {"role": "user", "content": "Show me your bracelets"},
      {"role": "assistant", "content": "..."}
    ]
  }'
```

### Windows PowerShell equivalent
```powershell
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post `
  -ContentType "application/json" `
  -Body '{"message": "Tell me about Noor"}'
```

---

## 5. Environment Variables

### Required (in `backend/.env`)
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1
QDRANT_URL=https://...cloud.qdrant.io
QDRANT_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small
CHAT_TIMEOUT_SECONDS=3
RAG_TIMEOUT_SECONDS=0.5
ROUTING_TIMEOUT_MS=200
LOG_LEVEL=INFO
```

### Verify env is loaded
```bash
uv run python -c "from app.config.settings import get_settings; print(get_settings().model_dump())"
```

---

## 6. Docker

### Build image
```bash
docker build -t aueshah-backend ./backend
```

### Run container
```bash
docker run --rm -p 8000:8000 --env-file backend/.env aueshah-backend
```

### Compose (full stack: backend + qdrant + ui)
```bash
docker-compose up --build         # foreground
docker-compose up -d              # detached
docker-compose logs -f backend    # tail backend logs
docker-compose down               # stop all
docker-compose down -v            # stop + remove volumes
```

---

## 7. Code Quality (optional tooling — not yet wired)

If/when added to dev deps:
```bash
uv add --dev ruff mypy
uv run ruff check app/            # lint
uv run ruff format app/           # format
uv run mypy app/                  # type-check
```

---

## 8. Quick Troubleshooting

| Symptom | Command |
|---|---|
| `ModuleNotFoundError` after pulling | `uv sync` |
| Stale lockfile after editing deps | `uv lock && uv sync` |
| Port 8000 already in use | `netstat -ano \| findstr :8000` (Windows) then kill PID |
| OpenAI auth errors | verify `OPENAI_API_KEY` in `.env`, then restart server |
| Qdrant timeouts | check `QDRANT_URL` reachability, raise `RAG_TIMEOUT_SECONDS` |
| Tests hang on async | confirm `asyncio_mode = "auto"` in `pyproject.toml` |

---

## 9. One-Liners (full restart cycle)

```bash
# Clean dev start
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000

# Run tests then start server
cd backend && uv run pytest tests/integration/ -v && uv run uvicorn app.main:app --reload --port 8000
```
