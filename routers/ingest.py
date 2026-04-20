from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
from supabase import create_client, Client
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.config import settings

router = APIRouter(prefix="/ingest", tags=["ingestion"])

class IngestResponse(BaseModel):
    message: str
    status: str

def run_ingestion_process():
    # Initialize API clients
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def embed_text(text: str) -> list[float]:
        response = openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    DOCS_DIR = "docs"

    if not os.path.exists(DOCS_DIR):
        print(f"Directory {DOCS_DIR} not found.")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=350,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".txt"):
            print(f"[{filename}] Cleaning previously stored versions in database...")
            try:
                supabase.table("documents").delete().eq("metadata->>source", filename).execute()
            except Exception as e:
                print(f"  Warning: {e}")

            file_path = os.path.join(DOCS_DIR, filename)
            try:
                # Try UTF-8 first, fallback to latin-1
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="latin-1") as file:
                        content = file.read()

                chunks = text_splitter.split_text(content)
                print(f"Processing {filename}: {len(chunks)} chunks generated.")

                for i, chunk in enumerate(chunks):
                    embedding = embed_text(chunk)
                    document_data = {
                        "content": chunk,
                        "metadata": {
                            "source": filename,
                            "chunk_index": i
                        },
                        "embedding": embedding
                    }
                    supabase.table("documents").insert(document_data).execute()
                    print(f"  Inserted chunk {i} for {filename}")
            except Exception as e:
                print(f"  Error processing file {filename}: {e}")

@router.post("/", response_model=IngestResponse)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Triggers the ingestion of documents into the vector database.
    Runs as a background task to prevent blocking the API response since it can be slow.
    """
    try:
        background_tasks.add_task(run_ingestion_process)
        return IngestResponse(
            message="Ingestion process started in the background.",
            status="processing"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
