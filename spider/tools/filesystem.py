from pathlib import Path


WORKSPACE = (
    Path(__file__).resolve().parents[2] / "workspace"
).resolve()


def _safe_path(relative_path: str) -> Path:
    candidate = (
        WORKSPACE / relative_path
    ).resolve()

    if candidate != WORKSPACE and WORKSPACE not in candidate.parents:
        raise PermissionError(
            "Path escapes the SPIDER workspace."
        )

    return candidate


async def list_workspace() -> str:
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    entries = []

    for item in sorted(WORKSPACE.iterdir()):
        prefix = "[DIR]" if item.is_dir() else "[FILE]"
        entries.append(f"{prefix} {item.name}")

    if not entries:
        return "Workspace is empty."

    return "\n".join(entries)


async def create_folder(path: str) -> str:
    target = _safe_path(path)

    target.mkdir(
        parents=True,
        exist_ok=True,
    )

    return f"Folder created: {target.relative_to(WORKSPACE)}"