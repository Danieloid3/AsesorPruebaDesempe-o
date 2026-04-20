# AI Support Assistant Backend

This is a production-ready AI customer support backend built with FastAPI, OpenAI, and Supabase (pgvector). It processes user queries, retrieves relevant context from a vector database (RAG - Retrieval-Augmented Generation), and generates grounded answers. 

## 🌐 Live Deployments
- **Backend API (Render):** [https://asesor-ai-backend.onrender.com](https://asesor-ai-backend.onrender.com)
- **Admin Dashboard (Lovable):** [https://linguatech-ai-compass.lovable.app/](https://linguatech-ai-compass.lovable.app/)

## Features
- **Retrieval-Augmented Generation (RAG):** Context strictly restricted to the academy's specific documents.
- **Workflow Automation Setup:** Ready to interact with n8n multichannel workflows via Webhooks.
- **Human Escalation:** Intelligent escalation logic for queries outside the known domains.
- **FAQ Caching:** Redis/In-Memory Cache to skip AI processing for repeated inquiries, reducing API costs.
- **Observability:** Stores track records for cost analysis, tokens used, and response quality metrics.

## Architecture

- **Frontend Dashboard:** A rich UI generated with Lovable to monitor operations, review escalated chats, and check metrics.
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
- n8n instance (Local, Cloud, or Docker)
- (Optional) Redis server for caching

## Automation Workflow (n8n)

This backend is designed to be fully integrated with **n8n** for handling multichannel messaging (Telegram, WhatsApp, Web, etc.).

1. **Webhook Trigger:** n8n listens for incoming messages from users (e.g., via Telegram).
2. **AI Processing:** n8n sends an HTTP POST request to the API `chat` endpoint containing the message and user ID.
3. **Decision Branch (Switch):**
   - If `escalate_to_human` is `false`, n8n replies directly to the user with the AI's provided `answer`.
   - If `escalate_to_human` is `true`, n8n routes the message to a human agent's inbox (or Slack/Telegram group) along with the `category` and context.
4. **Metrics:** Real-time logging of `cache_hit`, `confidence`, and `cost` straight into your dashboard.

A sample workflow file is included in this repository (`n8n_multicanal_workflow.json`). You can import this directly into your n8n workspace to get started immediately.

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

4. **Supabase Database Setup:**
   Run the following SQL code in your Supabase dashboard (SQL Editor) to enable Vector search and create the necessary schemas:
   ```sql
   -- Enable pgvector extension
   create extension if not exists vector;

   -- Create documents table
   create table documents (
     id bigserial primary key,
     content text,
     metadata jsonb,
     embedding vector(1536)
   );

   -- Create matching function (RPC) for RAG
   create or replace function match_documents (
     query_embedding vector(1536),
     match_threshold float,
     match_count int
   )
   returns table (
     id bigint,
     content text,
     metadata jsonb,
     similarity float
   )
   language sql stable
   as $$
     select
       documents.id,
       documents.content,
       documents.metadata,
       1 - (documents.embedding <=> query_embedding) as similarity
     from documents
     where 1 - (documents.embedding <=> query_embedding) > match_threshold
     order by documents.embedding <=> query_embedding
     limit match_count;
   $$;
   ```

5. **Ingest Documents:**
   Convert text documents from `docs/` into embeddings and store them in the vector database:
   ```bash
   python ingest.py
   ```

6. **Start the API server:**
   ```bash
   uvicorn main:app --reload
   ```

## Usage (API)

**1. Chat Endpoint:** `POST /api/v1/chat`

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

**2. Ingestion Endpoint:** `POST /api/v1/ingest/`
Triggers a background task to process, chunk, and embed `.txt` files from the `docs/` folder into Supabase without blocking the API.

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
