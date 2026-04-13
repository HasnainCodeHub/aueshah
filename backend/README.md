# AI Concierge Backend

Stateless FastAPI chat service with hybrid skill routing and RAG integration.

## Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key
- Qdrant instance (optional, mocked in Phase 1)

### Local Development (without Docker)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   export OPENAI_API_KEY=sk-...
   ```

4. **Run development server**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

   API will be available at `http://localhost:8000`

5. **Run tests**
   ```bash
   pytest
   ```

### Using Docker

```bash
docker-compose up -d
```

- Backend: http://localhost:8000
- Qdrant: http://localhost:6333
- Test UI: http://localhost:3000

## Project Structure

```
backend/
├── app/
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Orchestration, routing, prompt building
│   ├── services/         # AI client, RAG, failure handling
│   ├── skills/           # Skill implementations (product, compare, etc.)
│   ├── models/           # Pydantic schemas and errors
│   ├── config/           # Settings, prompts, routing rules
│   ├── utils/            # Logging, validation
│   └── main.py           # FastAPI app entry
├── tests/                # Unit and integration tests
├── requirements.txt      # Python dependencies
└── Dockerfile            # Container build
```

## API Endpoints

### POST /chat
Submit a chat message and receive an AI-generated reply.

**Request:**
```json
{
  "message": "Tell me about the Noor Collection",
  "context": [
    {"role": "user", "content": "What collections do you have?"},
    {"role": "assistant", "content": "We have several collections including Noor, Empire Allegiance, Velvet Line, and Luxura..."}
  ]
}
```

**Response (Success):**
```json
{
  "reply": "The Noor Collection is a limited edition of 143 handcrafted pieces...",
  "metadata": {
    "intent": "noor",
    "skill": "noor",
    "latency_ms": 1250,
    "routing_source": "rule"
  }
}
```

**Response (Error):**
```json
{
  "error": "I'm temporarily unable to provide a detailed response. Please try again.",
  "code": 503
}
```

### GET /health
Health check endpoint.

## Configuration

Edit `.env`:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Model to use (default: gpt-4-turbo-preview)
- `QDRANT_URL`: Vector store URL (default: http://localhost:6333)
- `CHAT_TIMEOUT_SECONDS`: Request timeout (default: 4)
- `LOG_LEVEL`: Logging level (default: INFO)

## Skill Routing

Hybrid routing strategy:
1. **Rule-based** (fast): Match keywords/patterns from `app/config/routing_rules.yaml`
2. **LLM fallback** (accurate): Lightweight OpenAI call for ambiguous intents
3. **Default**: Route to "general" skill if no match

Skills available:
- `product`: Describe a specific jewelry piece (ring, bracelet, earring, pendant, necklace, tiara, etc.)
- `compare`: Compare two pieces or collections
- `noor`: Acknowledge Noor Collection inquiries and refer to the team (stub in Phase 1)
- `bespoke`: Handle custom / made-to-order design requests (route to private concierge)
- `general`: Brand heritage, ethical sourcing, appointments, warranty, repairs

## RAG Integration

Retrieves top-3 knowledge chunks from Qdrant vector store to ground responses.

Currently mocked in Phase 1. To enable real RAG:
1. Set up Qdrant instance
2. Populate with indexed knowledge chunks (500–800 tokens each)
3. Update `app/services/rag_service.py` with actual retrieval logic

## Error Handling

**Retry Strategy:**
- 1–2 retries with exponential backoff (200ms, 500ms)
- Graceful fallback reply on exhaustion

**Safe Responses:**
- No API keys, system prompts, or stack traces leaked
- Fallback: "I'm temporarily unable to provide a detailed response. Please try again."

## Logging

Structured JSON logging to stdout. Fields:
- `timestamp`: ISO timestamp
- `level`: LOG_LEVEL
- `message`: Log message
- `component`: Code component (e.g., "orchestrator", "ai_client")
- `request_id`: Unique request identifier
- `intent`: Classified intent
- `skill`: Skill used
- `latency_ms`: Request latency

## Testing

Run all tests:
```bash
pytest
```

Run specific test:
```bash
pytest tests/integration/test_api_endpoint.py::test_chat_basic
```

Run with coverage:
```bash
pytest --cov=app
```

## Performance Targets

- **Latency**: p95 ≤ 3 seconds, p99 < 4 seconds
- **Success Rate**: 95% under normal load
- **Routing Latency**: < 100–200ms
- **RAG Latency**: < 500ms

## Deployment

### Docker

```bash
# Build
docker build -t concierge-backend backend/

# Run
docker run -e OPENAI_API_KEY=sk-... -p 8000:8000 concierge-backend
```

### Cloud (Recommended)

Deploy to cloud platforms supporting Python/FastAPI:
- AWS Lambda (with API Gateway)
- Google Cloud Run
- Azure Container Instances
- Heroku
- Railway
- Render

## Known Limitations (Phase 1)

- ❌ No authentication
- ❌ No persistent conversation storage
- ❌ RAG service mocked (no real vector store integration)
- ❌ No Noor tool execution (schema defined only)
- ❌ No rate limiting
- ❌ No advanced observability (tracing, custom metrics)

See `/specs/001-concierge-chat-api/tasks.md` for Phase 2+ work.

## Support

For issues or questions, see the architecture plan at `/specs/001-concierge-chat-api/plan.md`.
