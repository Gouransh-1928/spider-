import json
import re

from spider.agent.models import AgentPlan, ToolCall
from spider.llm.ollama import ollama


class AgentPlanner:
    async def plan(
        self,
        user_message: str,
        memory_context: str = "",
    ) -> AgentPlan:
        system_prompt = """
You are SPIDER's planning engine.

Your job is ONLY to convert the user's request into a valid JSON plan.

Return ONLY JSON.
Do not write explanations outside JSON.

Schema:
{
  "action": "respond" | "tool",
  "response": "string",
  "tool_call": {
    "name": "string",
    "arguments": {},
    "confirmed": false
  }
}

Available tools:

filesystem.list_workspace
- Lists files and folders in the SPIDER workspace.
- Arguments: {}

filesystem.create_folder
- Creates a folder inside the SPIDER workspace.
- Arguments:
  {
    "path": "folder/path"
  }

Rules:
1. Never invent a tool.
2. Never use shell commands.
3. Never claim an action was completed unless a tool actually executed.
4. If the user asks to create a folder, use filesystem.create_folder.
5. If the user asks to list/show workspace files, use filesystem.list_workspace.
6. For filesystem.create_folder, confirmed MUST be false unless the user explicitly confirms the operation.
7. If the request is not a tool request, use action="respond".
""".strip()

        prompt = f"""
MEMORY CONTEXT:
{memory_context or "(none)"}

USER REQUEST:
{user_message}
""".strip()

        raw = await ollama.generate(
            prompt=prompt,
            system=system_prompt,
            temperature=0.0,
        )

        plan = self._parse_plan(raw)

        # Safety-oriented deterministic correction.
        # The LLM is not allowed to turn a clear filesystem request
        # into an unrelated tool call or a false completion.
        corrected = self._correct_common_intents(
            user_message,
            plan,
        )

        return corrected

    def _parse_plan(self, raw: str) -> AgentPlan:
        text = raw.strip()

        # Remove accidental Markdown fences.
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        try:
            data = json.loads(text)
            return AgentPlan.model_validate(data)

        except Exception:
            return AgentPlan(
                action="respond",
                response=(
                    "I could not safely interpret that request."
                ),
            )

    def _correct_common_intents(
        self,
        user_message: str,
        plan: AgentPlan,
    ) -> AgentPlan:
        text = user_message.strip().lower()

        # ---------------------------------------------------------
        # CREATE FOLDER
        # ---------------------------------------------------------
        create_match = re.search(
            r"""
            (?:
                create|
                make|
                create\s+new|
                make\s+new
            )
            \s+
            (?:a\s+|an\s+|the\s+)?
            folder
            \s+
            (?:named\s+|called\s+)?
            ["']?([^"'.,!?]+)["']?
            """,
            text,
            flags=re.IGNORECASE | re.VERBOSE,
        )

        if create_match:
            folder_name = create_match.group(1).strip()

            return AgentPlan(
                action="tool",
                response=(
                    f"I can create the folder '{folder_name}', "
                    "but confirmation is required."
                ),
                tool_call=ToolCall(
                    name="filesystem.create_folder",
                    arguments={
                        "path": folder_name,
                    },
                    confirmed=False,
                ),
            )

        # ---------------------------------------------------------
        # LIST WORKSPACE
        # ---------------------------------------------------------
        if (
            "list workspace" in text
            or "show workspace" in text
            or "show my workspace" in text
            or "list files" in text
            or "show files" in text
        ):
            return AgentPlan(
                action="tool",
                response="I will inspect the SPIDER workspace.",
                tool_call=ToolCall(
                    name="filesystem.list_workspace",
                    arguments={},
                    confirmed=True,
                ),
            )

        # ---------------------------------------------------------
        # SAFETY CHECK
        # ---------------------------------------------------------
        if plan.action == "tool" and plan.tool_call:
            allowed = {
                "filesystem.list_workspace",
                "filesystem.create_folder",
            }

            if plan.tool_call.name not in allowed:
                return AgentPlan(
                    action="respond",
                    response=(
                        "I rejected that tool request because "
                        "the requested capability is not registered."
                    ),
                )

        return plan