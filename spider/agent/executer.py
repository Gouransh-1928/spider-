from typing import Any

from spider.agent.models import ToolCall
from spider.agent.registry import ToolRegistry
from spider.security.confirmation import ConfirmationStore


class ToolExecutor:
    """
    Final gate before a tool executes.
    """

    def __init__(
        self,
        confirmation_store: ConfirmationStore | None = None,
    ) -> None:
        self.registry = ToolRegistry()
        self.confirmations = (
            confirmation_store
            or ConfirmationStore()
        )

    async def prepare(
        self,
        conversation_id: int,
        tool_call: ToolCall,
    ) -> dict[str, Any]:
        tool = self.registry.get(tool_call.name)

        if tool is None:
            return {
                "success": False,
                "message": (
                    f"Unknown tool: {tool_call.name}"
                ),
            }

        if (
            tool.requires_confirmation
            and not tool_call.confirmed
        ):
            confirmation_id = (
                self.confirmations.create(
                    conversation_id=conversation_id,
                    tool_name=tool.name,
                    arguments=tool_call.arguments,
                )
            )

            return {
                "success": False,
                "requires_confirmation": True,
                "confirmation_id": confirmation_id,
                "tool": tool.name,
                "arguments": tool_call.arguments,
                "message": (
                    "Confirmation required."
                ),
            }

        return await self._execute_registered_tool(
            tool.name,
            tool.handler,
            tool_call.arguments,
        )

    async def execute_approved(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        tool = self.registry.get(tool_name)

        if tool is None:
            return {
                "success": False,
                "message": (
                    f"Unknown tool: {tool_name}"
                ),
            }

        return await self._execute_registered_tool(
            tool.name,
            tool.handler,
            arguments,
        )

    async def _execute_registered_tool(
        self,
        tool_name: str,
        handler: Any,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            result = await handler(**arguments)

            return {
                "success": True,
                "requires_confirmation": False,
                "tool": tool_name,
                "message": str(result),
            }

        except Exception as exc:
            return {
                "success": False,
                "requires_confirmation": False,
                "tool": tool_name,
                "message": (
                    f"Tool execution failed: {exc}"
                ),
            }