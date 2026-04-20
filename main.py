from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.chat import router as chat_router
from routers.ingest import router as ingest_router

app = FastAPI(
    title="Asesor AI Backend",
    description="Automated AI Assistant with RAG capabilities and n8n webhook integration.",
    version="1.0.0"
)

# CORS configuration to allow external services like n8n to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints mapping
app.include_router(chat_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "FastAPI AI Brain is running"}
