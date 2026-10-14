from dataclasses import dataclass
from typing import Any

from spider.agent.executer import ToolExecutor
from spider.agent.models import AgentPlan
from spider.agent.planner import AgentPlanner
from spider.security.confirmation import ConfirmationStore


@dataclass
class AgentResult:
    response: str
    plan: AgentPlan
    tool_result: dict[str, Any] | None = None


class AgentRuntime:
    def __init__(self) -> None:
        self.planner = AgentPlanner()

        self.confirmations = ConfirmationStore()

        self.executor = ToolExecutor(
            confirmation_store=self.confirmations,
        )

    async def run(
        self,
        conversation_id: int,
        user_message: str,
        memory_context: str = "",
    ) -> AgentResult:
        plan = await self.planner.plan(
            user_message=user_message,
            memory_context=memory_context,
        )

        if (
            plan.action != "tool"
            or plan.tool_call is None
        ):
            return AgentResult(
                response=(
                    plan.response
                    or "I understand your request."
                ),
                plan=plan,
            )

        tool_result = await self.executor.prepare(
            conversation_id=conversation_id,
            tool_call=plan.tool_call,
        )

        if tool_result.get(
            "requires_confirmation"
        ):
            confirmation_id = tool_result[
                "confirmation_id"
            ]

            tool_name = tool_result["tool"]

            response = (
                f"{plan.response}\n\n"
                f"Confirmation ID: {confirmation_id}\n"
                f"Tool: {tool_name}\n\n"
                "Please say 'yes' to approve "
                "or 'no' to reject."
            )

        else:
            response = tool_result.get(
                "message",
                "The operation was completed.",
            )

        return AgentResult(
            response=response,
            plan=plan,
            tool_result=tool_result,
        )

    async def approve_confirmation(
        self,
        conversation_id: int,
        confirmation_id: str,
    ) -> AgentResult:
        pending = self.confirmations.approve(
            confirmation_id=confirmation_id,
            conversation_id=conversation_id,
        )

        if pending is None:
            raise ValueError(
                "Confirmation is invalid, expired, "
                "already used, or belongs to another "
                "conversation."
            )

        result = await self.executor.execute_approved(
            tool_name=pending["tool_name"],
            arguments=pending["arguments"],
        )

        return AgentResult(
            response=result.get(
                "message",
                "Operation completed.",
            ),
            plan=AgentPlan(
                action="tool",
                response="Approved operation.",
            ),
            tool_result=result,
        )

    def reject_confirmation(
        self,
        conversation_id: int,
        confirmation_id: str,
    ) -> bool:
        return self.confirmations.reject(
            confirmation_id=confirmation_id,
            conversation_id=conversation_id,
        )