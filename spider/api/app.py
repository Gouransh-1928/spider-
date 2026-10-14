from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from spider.agent.runtime import AgentRuntime
from spider.core.config import settings
from spider.llm.ollama import ollama
from spider.memory.manager import MemoryManager
from spider.memory.store import MemoryStore


app = FastAPI(
    title="SPIDER",
    version="0.3.1",
    description="SPIDER local-first personal AI backend",
)

# ---------------------------------------------------------------------------
# Core services
# ---------------------------------------------------------------------------

memory_store = MemoryStore()
memory_manager = MemoryManager(memory_store)
agent_runtime = AgentRuntime()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str


class MemoryRequest(BaseModel):
    content: str
    memory_type: str = "fact"
    importance: int = 1


class ConfirmationRequest(BaseModel):
    conversation_id: int
    confirmation_id: str


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def authenticate(authorization: str | None) -> None:
    """
    Validate the SPIDER API bearer token.

    Authentication is only enforced when SPIDER_API_TOKEN is configured.
    """
    if not settings.spider_api_token:
        return

    expected = f"Bearer {settings.spider_api_token}"

    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    ollama_online = await ollama.health()

    return {
        "status": "ok",
        "model": settings.ollama_model,
        "ollama": ollama_online,
        "security": {
            "local_bind": settings.spider_host == "127.0.0.1",
            "api_auth": bool(settings.spider_api_token),
        },
        "agent": True,
        "memory": True,
        "confirmation": True,
    }


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

@app.post("/conversations")
async def create_conversation(
    authorization: str | None = Header(default=None),
):
    authenticate(authorization)

    conversation_id = memory_store.create_conversation()

    return {
        "conversation_id": conversation_id,
    }


# ---------------------------------------------------------------------------
# Long-term memory
# ---------------------------------------------------------------------------

@app.post("/memory")
async def save_memory(
    request: MemoryRequest,
    authorization: str | None = Header(default=None),
):
    authenticate(authorization)

    if not request.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Memory content cannot be empty.",
        )

    if not 1 <= request.importance <= 5:
        raise HTTPException(
            status_code=400,
            detail="Memory importance must be between 1 and 5.",
        )

    memory_id = memory_store.add_memory(
        content=request.content.strip(),
        memory_type=request.memory_type.strip(),
        importance=request.importance,
    )

    return {
        "memory_id": memory_id,
    }


# ---------------------------------------------------------------------------
# Chat / Agent
# ---------------------------------------------------------------------------

@app.post("/chat")
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
    authenticate(authorization)

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    # Create a conversation automatically when one wasn't supplied.
    conversation_id = request.conversation_id

    if conversation_id is None:
        conversation_id = memory_store.create_conversation()

    # Save the user's message before building memory context so future
    # requests can retrieve it.
    memory_store.add_message(
        conversation_id,
        "user",
        message,
    )

    # Retrieve only relevant memory + recent conversation.
    # This keeps llama3.1 context smaller and cheaper.
    context = memory_manager.build_context(
        conversation_id=conversation_id,
        query=message,
    )

    # Let AgentRuntime perform:
    #   memory-aware planning
    #   tool selection
    #   security/confirmation checks
    #   tool execution
    result = await agent_runtime.run(
        conversation_id=conversation_id,
        user_message=message,
        memory_context=context,
    )

    response = result.response

    # Persist SPIDER's response.
    memory_store.add_message(
        conversation_id,
        "assistant",
        response,
    )

    return {
        "conversation_id": conversation_id,
        "response": response,
        "plan": result.plan.model_dump(),
        "tool_result": result.tool_result,
    }


# ---------------------------------------------------------------------------
# Confirmation approval
# ---------------------------------------------------------------------------

@app.post("/confirm")
async def confirm(
    request: ConfirmationRequest,
    authorization: str | None = Header(default=None),
):
    authenticate(authorization)

    try:
        result = await agent_runtime.approve_confirmation(
            conversation_id=request.conversation_id,
            confirmation_id=request.confirmation_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # Store the result in conversation history.
    memory_store.add_message(
        request.conversation_id,
        "assistant",
        result.response,
    )

    return {
        "conversation_id": request.conversation_id,
        "response": result.response,
        "tool_result": result.tool_result,
    }


# ---------------------------------------------------------------------------
# Confirmation rejection
# ---------------------------------------------------------------------------

@app.post("/reject")
async def reject(
    request: ConfirmationRequest,
    authorization: str | None = Header(default=None),
):
    authenticate(authorization)

    rejected = agent_runtime.reject_confirmation(
        conversation_id=request.conversation_id,
        confirmation_id=request.confirmation_id,
    )

    if not rejected:
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirmation is invalid, expired, "
                "already used, or belongs to another conversation."
            ),
        )

    response = "The pending operation was rejected."

    memory_store.add_message(
        request.conversation_id,
        "assistant",
        response,
    )

    return {
        "conversation_id": request.conversation_id,
        "response": response,
    }