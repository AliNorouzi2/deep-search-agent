import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


class UploadManager:
    """Handles saving, deduplicating, and cleaning up user-uploaded PDF files."""

    def __init__(self, upload_dir: str = "uploads", max_files: int = 5):
        self.upload_dir = upload_dir
        self.max_files = max_files

    def save_uploaded_file(self, uploaded_file) -> str:
        """Save a single uploaded file to disk and return its path."""
        save_dir = Path(self.upload_dir)
        save_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = save_dir / f"Doc_{timestamp}_{uploaded_file.name}"

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return str(file_path)

    def deduplicate(self, uploaded_files: list) -> Tuple[list, List[str]]:
        """Keep only the first file for each duplicate name.
        Returns (deduped_files, skipped_names).
        """
        seen_names = set()
        deduped_files = []
        skipped_names = []

        for f in uploaded_files:
            if f.name in seen_names:
                skipped_names.append(f.name)
                continue
            seen_names.add(f.name)
            deduped_files.append(f)

        return deduped_files, skipped_names

    def enforce_limit(self, uploaded_files: list) -> Tuple[list, bool]:
        """Truncate to max_files. Returns (files, was_truncated)."""
        if len(uploaded_files) > self.max_files:
            return uploaded_files[: self.max_files], True
        return uploaded_files, False

    def process_uploads(self, uploaded_files: list, registry: Dict[str, str]) -> Dict:
        """Full pipeline: dedupe, enforce limit, save each file (replacing any
        previous file with the same name), and update the registry.

        Returns a dict with:
        {
            "file_paths": [...],
            "skipped_names": [...],
            "was_truncated": bool,
            "processed": [{"name": ..., "path": ...}, ...],
            "errors": [{"name": ..., "error": ...}, ...],
        }
        """
        deduped_files, skipped_names = self.deduplicate(uploaded_files)
        deduped_files, was_truncated = self.enforce_limit(deduped_files)

        file_paths = []
        processed = []
        errors = []

        for uploaded_file in deduped_files:
            file_name = uploaded_file.name
            try:
                if file_name in registry:
                    old_path = registry[file_name]
                    if os.path.exists(old_path):
                        os.remove(old_path)

                file_path = self.save_uploaded_file(uploaded_file)
                file_paths.append(file_path)
                registry[file_name] = file_path
                processed.append({"name": file_name, "path": file_path})
            except Exception as e:
                errors.append({"name": file_name, "error": str(e)})

        return {
            "file_paths": file_paths,
            "skipped_names": skipped_names,
            "was_truncated": was_truncated,
            "processed": processed,
            "errors": errors,
        }

    def cleanup(self, registry: Dict[str, str]) -> None:
        """Remove the entire upload directory and recreate it empty. Clears the registry."""
        upload_dir = Path(self.upload_dir)
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            upload_dir.mkdir(exist_ok=True)
        registry.clear()