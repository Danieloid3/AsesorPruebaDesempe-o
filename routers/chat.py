from fastapi import APIRouter
from schemas.chat import ChatRequest, ChatResponse
from services.cache import get_cached_response, set_cached_response, get_chat_history, add_to_chat_history, log_metrics, get_dashboard_metrics
from services.rag import orchestrate_rag_pipeline
from services.analytics import save_chat_log
import traceback

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    """
    Webhook endpoint to be consumed by n8n.
    Receives JSON containing message from Telegram/Whatsapp and processes it through the entire Backend pipeline.
    """
    user_query = request.message
    user_id = request.user_id
    channel = request.channel

    # Retrieve history for context
    history = get_chat_history(user_id)

    # 1. Check Redis Cache First ($0 cost for repeated queries)
    # We only use simple cache if there is NO conversation history yet,
    # because context-dependent queries like "si los precios" shouldn't hit generic cache.
    if not history:
        cached_res = get_cached_response(user_query)
        if cached_res:
            # If cache hits, tag it as cache hit and return directly
            cached_res["cache_hit"] = True
            cached_res["user_id"] = user_id
            cached_res["channel"] = channel

            # Log zero-cost cache hit
            log_metrics(0.0, cached_res.get("escalate_to_human", False), True)

            # Save interaction history in Supabase
            save_chat_log({
                "user_id": user_id,
                "channel": channel,
                "user_query": user_query,
                "ai_answer": cached_res.get("answer", ""),
                "escalate_to_human": cached_res.get("escalate_to_human", False),
                "category": cached_res.get("category", "Unknown"),
                "cache_hit": True,
                "cost": 0.0,
                "tokens_used": 0
            })

            return ChatResponse(**cached_res)

    try:
        # 2. RAG Missing Cache: Embeddings -> Supabase -> OpenAI Prompt
        response_dict = orchestrate_rag_pipeline(user_query, history)

        # Extract metrics to log
        metrics = response_dict.pop("_metrics", {})
        request_cost = metrics.get("total_cost", 0.0)
        tokens_used = metrics.get("tokens_used", 0)

        # 3. Save RAG Answer back to Redis Cache
        # Only cache if it's the first message
        if not history:
            set_cached_response(user_query, response_dict)

        # Append to conversation history
        add_to_chat_history(user_id, user_query, response_dict["answer"])

        # 4. Return properly formatted payload
        response_dict["user_id"] = user_id
        response_dict["channel"] = channel

        # Log completion metrics
        log_metrics(request_cost, response_dict.get("escalate_to_human", False), False)

        # Save interaction history in Supabase
        save_chat_log({
            "user_id": user_id,
            "channel": channel,
            "user_query": user_query,
            "ai_answer": response_dict.get("answer", ""),
            "escalate_to_human": response_dict.get("escalate_to_human", False),
            "category": response_dict.get("category", "Unknown"),
            "cache_hit": False,
            "cost": request_cost,
            "tokens_used": tokens_used
        })

        # 5. Return the Pydantic structured output
        return ChatResponse(**response_dict)

    except Exception as e:
        print(f"Error processing RAG Pipeline: {traceback.format_exc()}")

        # Log failure logic as escalation
        log_metrics(0.0, True, False)

        save_chat_log({
            "user_id": user_id,
            "channel": channel,
            "user_query": user_query,
            "ai_answer": "Lo siento, estoy experimentando dificultades técnicas. Te conectaré con un agente humano.",
            "escalate_to_human": True,
            "category": "Error Técnico",
            "cache_hit": False,
            "cost": 0.0,
            "tokens_used": 0
        })

        # Fallback security on AI Provider / DB error
        return ChatResponse(
            answer="Lo siento, estoy experimentando dificultades técnicas. Te conectaré con un agente humano.",
            escalate_to_human=True,
            category="Error Técnico",
            cache_hit=False,
            user_id=user_id,
            channel=channel
        )

@router.get("/metrics")
async def process_metrics():
    """Returns basic performance and cost metrics for the business."""
    return get_dashboard_metrics()
