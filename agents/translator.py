import re
import logging
import unicodedata
from typing import List, Dict, Tuple
import argostranslate.package
import argostranslate.translate

logger = logging.getLogger(__name__)


class Translator:
    def __init__(self):
        self.from_code = "en"
        self.to_code = "fa"
        # Smaller chunks = Argos repeats less
        self.max_chunk_chars = 300
        # Markers we recognize inside markdown
        self.marker_chars = ["**", "__", "*", "_", "`"]
        self._ensure_package_installed()

    def _ensure_package_installed(self):
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        package_to_install = next(
            filter(
                lambda x: x.from_code == self.from_code and x.to_code == self.to_code,
                available_packages
            ),
            None
        )
        if package_to_install is None:
            raise RuntimeError(
                f"No translation package found for {self.from_code} -> {self.to_code}"
            )

        installed_packages = argostranslate.package.get_installed_packages()
        already_installed = any(
            p.from_code == self.from_code and p.to_code == self.to_code
            for p in installed_packages
        )
        if not already_installed:
            logger.info(f"[Translator] Downloading package: {self.from_code} -> {self.to_code}")
            argostranslate.package.install_from_path(package_to_install.download())

    # ---------- cleanup ----------

    def _clean_invisible(self, text: str) -> str:
        result = []
        for ch in text:
            cat = unicodedata.category(ch)
            if cat in ("Co", "Cn"):
                continue
            if cat == "Cc" and ch not in ("\n", "\t", "\r"):
                continue
            if ch == "\ufffd":
                continue
            if ch in ("\u200b", "\u200d", "\u200e", "\u200f",
                      "\u202a", "\u202b", "\u202c", "\u202d", "\u202e"):
                continue
            result.append(ch)
        return "".join(result)

    def _strip_broken_markers(self, text: str) -> str:
        """Remove any dangling ⟨ or ⟩ left by Argos."""
        # Remove lone angle brackets with optional digits/spaces
        text = re.sub(r"⟨\s*\d*\s*", "", text)
        text = re.sub(r"\s*\d*\s*⟩", "", text)
        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text)
        return text

    def _balance_markdown(self, text: str) -> str:
        """Ensure ** and * come in pairs. Remove unbalanced ones."""
        for marker in ["**", "*"]:
            # Skip ** when counting * to avoid double-count
            if marker == "*":
                # Temporarily remove ** to count single *
                temp = text.replace("**", "")
                count = temp.count("*")
            else:
                count = text.count("**")

            if count % 2 == 1:
                # Remove the last unmatched marker
                idx = text.rfind(marker)
                if idx != -1:
                    text = text[:idx] + text[idx + len(marker):]
        return text

    def _remove_duplicate_runs(self, text: str) -> str:
        """Collapse repeated word sequences like 'Agent Agent Agent Agent'."""
        # Split into lines and process each
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            # Collapse 3+ repeats of the same word
            line = re.sub(r"\b(\w+)(?:\s+\1\b){2,}", r"\1", line)
            # Collapse repeated punctuation
            line = re.sub(r"([.:،])\1{2,}", r"\1", line)
            cleaned.append(line)
        return "\n".join(cleaned)

    # ---------- markers ----------

    def _extract_markers(self, text: str) -> Tuple[str, List[Dict]]:
        """Extract markdown markers and replace with safe tokens."""
        markers = []
        # Match longest first so ** isn't split into two *
        pattern = r"\*\*|__|`|\*|_"

        def repl(match):
            idx = len(markers)
            # Use rare unicode char that Argos won't tokenize away
            token = f"\u2039{idx}\u203a"  # ‹0› ‹1› ...
            markers.append({
                "index": idx,
                "token": token,
                "marker": match.group(0),
                "position": match.start(),
            })
            return token

        clean_text = re.sub(pattern, repl, text)
        return clean_text, markers

    def _restore_markers(self, translated: str, markers: List[Dict]) -> str:
        """Restore markdown markers. Handle lost/broken tokens."""
        if not markers:
            return translated

        result = translated

        # Pass 1: normal token restore
        for m in markers:
            if m["token"] in result:
                result = result.replace(m["token"], m["marker"])

        # Pass 2: restore partially-broken tokens (Argos may drop the close ›)
        for m in markers:
            idx = m["index"]
            # Try variants: ‹0›, ‹0, ‹ 0 ›, etc.
            variants = [
                f"\u2039{idx}\u203a",
                f"\u2039{idx}",
                f"\u2039 {idx} \u203a",
                f"\u2039 {idx}",
            ]
            for v in variants:
                if v in result:
                    result = result.replace(v, m["marker"])
                    break

        return result

    # ---------- chunking ----------

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split into sentence-level chunks to keep Argos stable."""
        # Split on sentence boundaries while keeping the delimiter
        parts = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current = ""

        for part in parts:
            if len(current) + len(part) + 1 <= self.max_chunk_chars:
                current = f"{current} {part}".strip()
            else:
                if current:
                    chunks.append(current)
                # If single sentence is too long, split on commas
                if len(part) > self.max_chunk_chars:
                    sub_parts = re.split(r"(?<=[,;:])\s+", part)
                    sub_current = ""
                    for sp in sub_parts:
                        if len(sub_current) + len(sp) + 1 <= self.max_chunk_chars:
                            sub_current = f"{sub_current} {sp}".strip()
                        else:
                            if sub_current:
                                chunks.append(sub_current)
                            sub_current = sp
                    if sub_current:
                        chunks.append(sub_current)
                    current = ""
                else:
                    current = part

        if current:
            chunks.append(current)

        return chunks

    def _translate_one(self, chunk: str) -> str:
        try:
            translated = argostranslate.translate.translate(
                chunk, self.from_code, self.to_code
            )
            return (translated or "").strip()
        except Exception as e:
            logger.error(f"[Translator] chunk failed: {e}")
            return chunk

    # ---------- public API ----------

    def translate_to_persian(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        # 1. Clean invisible chars
        text = self._clean_invisible(text)

        # 2. Split by paragraphs first
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        all_translated = []
        for para in paragraphs:
            # 3. Extract markers per paragraph
            clean_para, markers = self._extract_markers(para)

            # 4. Split into sentences and translate each
            chunks = self._split_into_sentences(clean_para)
            translated_chunks = []
            for i, chunk in enumerate(chunks, start=1):
                t = self._translate_one(chunk)
                if t:
                    translated_chunks.append(t)

            para_translated = " ".join(translated_chunks)

            # 5. Restore markers
            para_translated = self._restore_markers(para_translated, markers)

            # 6. Clean up broken markers and duplicates
            para_translated = self._strip_broken_markers(para_translated)
            para_translated = self._remove_duplicate_runs(para_translated)
            para_translated = self._balance_markdown(para_translated)

            all_translated.append(para_translated)

        result = "\n\n".join(all_translated)
        result = self._clean_invisible(result)
        return result