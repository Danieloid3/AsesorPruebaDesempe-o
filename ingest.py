import os
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

# Initialize API clients
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DOCS_DIR = "docs"

def embed_text(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def main():
    if not os.path.exists(DOCS_DIR):
        print(f"Directory {DOCS_DIR} not found.")
        return

    # Increase chunk_size to 1200 and overlap to 350
    # to ensure larger context without weird paragraph breaks.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=350,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".txt"):

            # 1. Delete previous chunks of this file to prevent duplicate data in Supabase
            print(f"[{filename}] Cleaning previously stored versions in database...")
            try:
                # Requires appropriate RLS policies or a service key with proper permissions.
                supabase.table("documents").delete().eq("metadata->>source", filename).execute()
            except Exception as e:
                print(f"  Warning (Could not clean, ignore if first time running or missing permissions): {e}")

            file_path = os.path.join(DOCS_DIR, filename)
            try:
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="latin-1") as file:
                        content = file.read()

                # Create chunks
                chunks = text_splitter.split_text(content)
                print(f"Processing {filename}: {len(chunks)} chunks generated.")

                for i, chunk in enumerate(chunks):
                    # Request embedding
                    embedding = embed_text(chunk)

                    # Prepare metadata and document record
                    document_data = {
                        "content": chunk,
                        "metadata": {
                            "source": filename,
                            "chunk_index": i
                        },
                        "embedding": embedding
                    }

                    # Insert into Supabase `documents` table
                    response = supabase.table("documents").insert(document_data).execute()
                    print(f"  Inserted chunk {i} for {filename}")
            except Exception as e:
                print(f"  [ERROR] Se detuvo el procesamiento de {filename} por un error: {e}")

if __name__ == "__main__":
    main()
