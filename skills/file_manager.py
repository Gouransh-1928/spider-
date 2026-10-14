"""
SPIDER — File Manager Skill
Handles natural language → file system operations on Windows.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger


class FileManager:
    """
    Handles file and folder operations for SPIDER.
    Supports: create, delete, rename, copy, move, open, list.
    """

    def __init__(self):
        self.home = Path.home()
        self.desktop = self.home / "Desktop"
        self.downloads = self.home / "Downloads"
        self.documents = self.home / "Documents"

        # Alias map for natural language locations
        self.location_aliases = {
            "desktop": self.desktop,
            "downloads": self.downloads,
            "documents": self.documents,
            "home": self.home,
            "d drive": Path("D:/"),
            "c drive": Path("C:/"),
        }

    def handle(self, user_input: str) -> str:
        """Parse user command and execute the appropriate file operation."""
        text = user_input.lower()

        if any(w in text for w in ["create folder", "make folder", "new folder", "create directory"]):
            return self._create_folder(user_input)
        elif any(w in text for w in ["delete folder", "remove folder", "delete file", "remove file"]):
            return self._delete(user_input)
        elif "rename" in text:
            return self._rename(user_input)
        elif any(w in text for w in ["copy file", "copy folder"]):
            return self._copy(user_input)
        elif any(w in text for w in ["move file", "move folder", "cut and paste"]):
            return self._move(user_input)
        elif any(w in text for w in ["open file", "open folder", "open the"]):
            return self._open(user_input)
        elif any(w in text for w in ["list files", "show files", "what files", "files in"]):
            return self._list_files(user_input)
        else:
            return "I understand you want to do something with files, but I need more details. What exactly should I do?"

    def _create_folder(self, text: str) -> str:
        """Create a new folder."""
        name, location = self._extract_name_and_location(text)
        if not name:
            return "What should I name the folder?"

        target = (location / name) if location else (self.desktop / name)
        try:
            target.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created folder: {target}")
            return f"Done! I created the folder '{name}' at {target}"
        except Exception as e:
            logger.error(f"Folder creation error: {e}")
            return f"I couldn't create the folder. Error: {e}"

    def _delete(self, text: str) -> str:
        """Delete a file or folder."""
        name, location = self._extract_name_and_location(text)
        if not name:
            return "What should I delete?"

        target = self._find_path(name, location)
        if not target or not target.exists():
            return f"I couldn't find '{name}'. Could you check the name or location?"

        try:
            if target.is_dir():
                shutil.rmtree(target)
                return f"Done! I deleted the folder '{name}'."
            else:
                target.unlink()
                return f"Done! I deleted the file '{name}'."
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return f"I couldn't delete it. Error: {e}"

    def _rename(self, text: str) -> str:
        """Rename a file or folder."""
        # Try to extract: "rename X to Y"
        match = re.search(r'rename\s+["\']?(.+?)["\']?\s+to\s+["\']?(.+?)["\']?$', text, re.IGNORECASE)
        if not match:
            return "Please say: 'rename [old name] to [new name]'"

        old_name = match.group(1).strip()
        new_name = match.group(2).strip()

        # Search desktop and common locations
        for base in [self.desktop, self.documents, self.downloads, self.home]:
            old_path = base / old_name
            if old_path.exists():
                new_path = old_path.parent / new_name
                try:
                    old_path.rename(new_path)
                    return f"Done! Renamed '{old_name}' to '{new_name}'."
                except Exception as e:
                    return f"Couldn't rename: {e}"

        return f"I couldn't find '{old_name}'. Could you tell me where it is?"

    def _copy(self, text: str) -> str:
        """Copy a file or folder."""
        # Simple pattern: "copy [name] to [location]"
        match = re.search(r'copy\s+["\']?(.+?)["\']?\s+to\s+(.+)', text, re.IGNORECASE)
        if not match:
            return "Please say: 'copy [name] to [location]'"

        src_name = match.group(1).strip()
        dest_text = match.group(2).strip()

        src = self._find_path(src_name)
        dest_dir = self._resolve_location(dest_text) or self.desktop

        if not src or not src.exists():
            return f"I couldn't find '{src_name}'."

        try:
            dest = dest_dir / src.name
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
            return f"Done! Copied '{src_name}' to {dest_dir}."
        except Exception as e:
            return f"Couldn't copy: {e}"

    def _move(self, text: str) -> str:
        """Move a file or folder."""
        match = re.search(r'move\s+["\']?(.+?)["\']?\s+to\s+(.+)', text, re.IGNORECASE)
        if not match:
            return "Please say: 'move [name] to [location]'"

        src_name = match.group(1).strip()
        dest_text = match.group(2).strip()

        src = self._find_path(src_name)
        dest_dir = self._resolve_location(dest_text) or self.desktop

        if not src or not src.exists():
            return f"I couldn't find '{src_name}'."

        try:
            shutil.move(str(src), str(dest_dir / src.name))
            return f"Done! Moved '{src_name}' to {dest_dir}."
        except Exception as e:
            return f"Couldn't move: {e}"

    def _open(self, text: str) -> str:
        """Open a file or folder in the default application / Explorer."""
        name, location = self._extract_name_and_location(text)
        if not name:
            return "What should I open?"

        target = self._find_path(name, location)
        if not target or not target.exists():
            return f"I couldn't find '{name}'."

        try:
            os.startfile(str(target))
            return f"Opening '{name}'!"
        except Exception as e:
            return f"Couldn't open it: {e}"

    def _list_files(self, text: str) -> str:
        """List files in a directory."""
        _, location = self._extract_name_and_location(text)
        target = location or self.desktop

        if not target.exists():
            return f"That location doesn't exist: {target}"

        try:
            items = list(target.iterdir())
            if not items:
                return f"The folder '{target.name}' is empty."

            folders = [f"📁 {i.name}" for i in items if i.is_dir()]
            files = [f"📄 {i.name}" for i in items if i.is_file()]
            result = "\n".join(folders + files)
            return f"Contents of {target}:\n{result}"
        except Exception as e:
            return f"Couldn't list files: {e}"

    def _extract_name_and_location(self, text: str) -> Tuple[Optional[str], Optional[Path]]:
        """Extract folder/file name and location from natural language."""
        # Extract location
        location = None
        for alias, path in self.location_aliases.items():
            if alias in text.lower():
                location = path
                break

        # Extract name — look for quoted or specific keywords
        name_match = re.search(
            r'(?:called|named|folder|file|directory)\s+["\']?([A-Za-z0-9_\-\. ]+?)["\']?'
            r'(?:\s+on|\s+in|\s+at|\s+to|$)',
            text,
            re.IGNORECASE,
        )
        name = name_match.group(1).strip() if name_match else None

        return name, location

    def _find_path(self, name: str, hint_location: Optional[Path] = None) -> Optional[Path]:
        """Search for a file/folder by name across common locations."""
        search_dirs = [hint_location] if hint_location else []
        search_dirs += [self.desktop, self.documents, self.downloads, self.home]

        for directory in search_dirs:
            if directory is None:
                continue
            candidate = directory / name
            if candidate.exists():
                return candidate

        return None

    def _resolve_location(self, text: str) -> Optional[Path]:
        """Resolve a natural language location string to a Path."""
        text_lower = text.lower().strip()
        for alias, path in self.location_aliases.items():
            if alias in text_lower:
                return path
        # Try as absolute path
        try:
            p = Path(text)
            if p.exists():
                return p
        except Exception:
            pass
        return None
