from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's query received from n8n.")
    user_id: str = Field(..., description="A unique identifier for the user.")
    channel: str = Field(..., description="The channel where the message came from (e.g., telegram, whatsapp, web).")

class AIResponse(BaseModel):
    answer: str = Field(..., description="The grounded AI response generated via RAG.")
    escalate_to_human: bool = Field(..., description="True if the question is out of scope and requires human fallback.")
    category: str = Field(..., description="The inferred topic category of the conversation.")

class ChatResponse(AIResponse):
    cache_hit: bool = Field(..., description="True if the response was served from Redis without hitting OpenAI.")
    user_id: str = Field(..., description="The original user ID passed in the request.")
    channel: str = Field(..., description="The original channel passed in the request.")
