from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


class AgentPlan(BaseModel):
    action: Literal["respond", "tool"] = "respond"
    response: str = ""
    tool_call: ToolCall | None = None