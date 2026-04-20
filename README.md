# AI Support Assistant Backend

This is a production-ready AI customer support backend built with FastAPI, OpenAI, and Supabase (pgvector). It processes user queries, retrieves relevant context from a vector database (RAG - Retrieval-Augmented Generation), and generates grounded answers. 

## Features
- **Retrieval-Augmented Generation (RAG):** Context strictly restricted to the academy's specific documents.
- **Workflow Automation Setup:** Ready to interact with n8n multichannel workflows via Webhooks.
- **Human Escalation:** Intelligent escalation logic for queries outside the known domains.
- **FAQ Caching:** Redis/In-Memory Cache to skip AI processing for repeated inquiries, reducing API costs.
- **Observability:** Stores track records for cost analysis, tokens used, and response quality metrics.

## Architecture

- `core/`: Application settings and database connections.
- `routers/`: FastAPI routes (e.g., chat/webhook endpoints).
- `schemas/`: Pydantic models for predictable and validated data contracts.
- `services/`: Business logic, RAG retrieval (`rag.py`), AI interaction (`openai_llm.py`), caching (`cache.py`), analytics (`analytics.py`).
- `docs/`: Plain text files used as knowledge base.
- `ingest.py`: Script to process, chunk, embed, and store documents in Supabase.

## Requirements Requirements
- Python 3.10+
- OpenAI API Key
- Supabase Project (with Vector Extension enabled)
- (Optional) Redis server for caching

## Setup & Installation

1. **Clone the repo and navigate to the folder:**
   ```bash
   git clone <repo-url>
   cd AsesorPrueba
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment Setup:**
   Copy the example environment file and fill it with your credentials:
   ```bash
   cp .env.example .env
   ```
   Add your keys:
   - `OPENAI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

4. **Ingest Documents:**
   Convert text documents from `docs/` into embeddings and store them in the vector database:
   ```bash
   python ingest.py
   ```

5. **Start the API server:**
   ```bash
   uvicorn main:app --reload
   ```

## Usage (API)

**Endpoint:** `POST /chat`

```json
{
  "user_id": "12345",
  "message": "What is the cost of the inscription?"
}
```

**Response Contract:**
```json
{
  "answer": "Based on our policies, the inscription costs $50 USD.",
  "escalate_to_human": false,
  "confidence": 0.95,
  "category": "Pricing",
  "cache_hit": false
}
```

## Running with Docker

You can also run the whole backend via Docker:

```bash
docker-compose up --build
```

**Note on Docker Compose:** `docker-compose.yml` mounts the API, Redis, and n8n together. This is ideal for local development or deploying to a VPS (like DigitalOcean or AWS EC2).

## Deploying to Render (or other PaaS)

To deploy to Render (Vercel, Railway, etc.):

1. **Deploy the Database/Cache:** Render doesn't use `docker-compose.yml` natively. You must first create a **Redis** instance in Render (or use Upstash) and copy its Internal/External Connection URL.
2. **Deploy the API:** 
   - Create a new **Web Service** in Render.
   - Connect your GitHub repository.
   - Choose **Docker** as the environment (Render will automatically use the `Dockerfile`).
   - Add your Environment Variables (`OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, and the `REDIS_URL` from step 1).
   - Render will automatically inject a `PORT` environment variable and start the application.
