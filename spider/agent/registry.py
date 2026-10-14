from dataclasses import dataclass
from typing import Any, Awaitable, Callable


ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    requires_confirmation: bool
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

        self.register(
            RegisteredTool(
                name="filesystem.list_workspace",
                description="List files and folders in the SPIDER workspace.",
                requires_confirmation=False,
                handler=self._list_workspace,
            )
        )

        self.register(
            RegisteredTool(
                name="filesystem.create_folder",
                description="Create a folder inside the SPIDER workspace.",
                requires_confirmation=True,
                handler=self._create_folder,
            )
        )

    def register(self, tool: RegisteredTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    async def _list_workspace(self) -> str:
        from spider.tools.filesystem import list_workspace

        return await list_workspace()

    async def _create_folder(self, path: str) -> str:
        from spider.tools.filesystem import create_folder

        return await create_folder(path)