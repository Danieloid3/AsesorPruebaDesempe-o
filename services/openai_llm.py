import json
from openai import OpenAI
from schemas.chat import AIResponse
from core.config import settings

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Custom System Prompt that restricts the AI (RAG Constraints) and shapes personality
SYSTEM_PROMPT = """You are an expert, professional, and friendly Customer Support Assistant for our academy.
Your main job is to help users by answering their questions BASED STRICTLY AND ONLY ON THE CONTEXT PROVIDED.

*** CRITICAL RULES ***
1. If the user is just saying a simple greeting or thanking you (e.g. 'hola', 'buenos días', 'gracias'), greet them warmly, ask how you can help, and SET "escalate_to_human" to false. Do not claim you don't know the answer to a greeting.
2. YOU MUST NEVER INVENT INFORMATION. If the user asks a factual question about the academy and the answer is not in the context, you MUST set "escalate_to_human" to true and kindly explain that you cannot find the requested information. Note: Treat terms like 'cursos', 'clases', 'programas', and 'niveles' as synonyms.
3. DO NOT MENTION THE CONTEXT EXPLICITLY. Say "Based on our policies" instead of "Based on the provided document".
4. Provide concise, grounded answers.
5. Escalate to a human agent when the user is aggressive, asks about something totally unrelated to the academy (that is not a greeting), or requests it directly.
6. In the "category" field, classify the query into one of: "Greeting", "Pricing", "Schedules", "Certifications", "Other".

*** FEW-SHOT EXAMPLES ***

Example 1 (Greeting):
User: Hola, buenos días.
AI: ¡Hola, buenos días! ¿En qué te puedo ayudar hoy con respecto a nuestra academia?
(escalate: false, category: Greeting)

Example 2 (Out of scope / Not in context):
User: ¿Cuál es el menú de la cafetería?
AI: Lo siento, pero no tengo información sobre el menú de la cafetería. Un agente humano se pondrá en contacto contigo para ayudarte.
(escalate: true, category: Other)

Example 3 (In context - Pricing):
User: ¿Cuánto cuesta la inscripción?
AI: Basado en nuestras políticas, la inscripción tiene un costo de $50 USD.
(escalate: false, category: Pricing)
"""

def generate_rag_answer(query: str, context: str, history: list = None) -> dict:
    """Generate the definitive AI response using OpenAI's Structured Outputs (JSON Schema)."""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        # Include history so RAG knows the context of "si, los precios"
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"Context information:\n---------------------\n{context}\n---------------------\n\nUser Question: {query}"
    })

    # Using gpt-4o-mini with JSON response format enforced.
    response = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        response_format=AIResponse,
        temperature=0.2,
    )

    # Calculate Estimated Cost
    # gpt-4o-mini: $0.15 / 1M input tokens, $0.60 / 1M output tokens
    in_tokens = response.usage.prompt_tokens
    out_tokens = response.usage.completion_tokens
    estimated_cost = (in_tokens / 1_000_000) * 0.15 + (out_tokens / 1_000_000) * 0.60

    # Convert the structured response back into a dictionary matching our expected schema.
    parsed_response = response.choices[0].message.parsed
    # Overwrite cache_hit locally to False (since we generated a novel answer)
    response_dict = parsed_response.model_dump()
    response_dict["cache_hit"] = False

    # Add hidden metric fields to pass it down the pipeline
    response_dict["_metrics"] = {
        "cost": estimated_cost,
        "tokens_used": in_tokens + out_tokens
    }

    return response_dict
