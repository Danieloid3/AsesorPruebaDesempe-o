from core.db import supabase
from services.openai_llm import openai_client, generate_rag_answer

def embed_query(query: str) -> list[float]:
    """Convert the raw text into an embedding vector."""
    response = openai_client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def retrieve_documents(embedding: list[float], match_threshold: float = 0.5, match_count: int = 4) -> str:
    """Search vector database by calling Supabase RPC match_documents, format context."""

    # We use the RPC defined in your instructions: match_documents(query_embedding, match_threshold, match_count)
    response = supabase.rpc("match_documents", {
        "query_embedding": embedding,
        "match_threshold": match_threshold,
        "match_count": match_count
    }).execute()

    docs = response.data

    # Check if there are matches at all
    if not docs:
        return ""

    # Combine chunks into a single readable context
    context = "\n---\n".join([doc["content"] for doc in docs])
    return context

def rewrite_query_with_history(query: str, history: list) -> str:
    """Rewrite the user's query to make it standalone using chat history."""
    if not history:
        return query, 0.0

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Rewrite the latest user query so it can be used for a standalone document search, incorporating context from the conversation history if necessary. Return ONLY the rewritten query text."}
    ]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": f"Rewrite this query: {query}"})

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.0
    )

    # Calculate cost
    in_tokens = response.usage.prompt_tokens
    out_tokens = response.usage.completion_tokens
    estimated_cost = (in_tokens / 1_000_000) * 0.15 + (out_tokens / 1_000_000) * 0.60

    return response.choices[0].message.content.strip(), estimated_cost

def orchestrate_rag_pipeline(query: str, history: list = None) -> dict:
    """The central RAG engine that connects Embedding -> Retrieval -> LLM Generation."""

    total_cost = 0.0

    # 0. Rewrite query based on history to improve retrieval
    if history:
        search_query, rewrite_cost = rewrite_query_with_history(query, history)
        total_cost += rewrite_cost
    else:
        search_query = query

    # 1. Embed user query using the improved search query
    query_vector = embed_query(search_query)

    # 1.5 Embed cost (text-embedding-3-small: $0.02 / 1M tokens)
    # Estimate roughly based on character count / 4 for simplicity, or we can just ignore it since it's negligible.
    total_cost += (len(search_query) / 4 / 1_000_000) * 0.02

    # 2. Retrieve top chunks associated with query
    context_text = retrieve_documents(query_vector)

    # 3. If there is no context found AT ALL, we pass an empty string instead of failing blindly,
    # so the LLM can still reply to basic greetings like "hola".
    if not context_text:
        context_text = "No relevant context found in the database."

    # 4. Generate AI Answer using grounded context, passing history for conversational flow
    response_dict = generate_rag_answer(query, context_text, history)

    # Accumulate costs and pass them to the router
    metrics = response_dict.pop("_metrics", {})
    total_cost += metrics.get("cost", 0.0)

    response_dict["_metrics"] = {
        "total_cost": total_cost,
        "tokens_used": metrics.get("tokens_used", 0)
    }

    return response_dict
