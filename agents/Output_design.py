from typing import List, Dict
from openai import OpenAI


class OutputDesigner:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)  # key unused by Ollama

    def build_references(self, summarized_docs: List[Dict]) -> List[str]:
        """Build a numbered reference list from the analyzed documents."""
        references = []
        for i, doc in enumerate(summarized_docs, start=1):
            title = doc.get("file_path", "Unknown source")
            if doc.get("source") == "external_agent" and doc.get("pdf_url"):
                references.append(f"[{i}] {title} — {doc['pdf_url']}")
            else:
                references.append(f"[{i}] {title} (user-uploaded document)")
        return references

    def generate_article(
        self,
        user_text: str,
        summarized_docs: List[Dict],
        conclusion_max_tokens: int = 900,
    ) -> Dict:
        """Generate a full research-article-style output: Introduction, Body,
        Conclusion (length scaled by conclusion_max_tokens), and References.
        """
        combined_summaries = "\n\n---\n\n".join(
            f"[Source {i+1}: {d.get('file_path', 'n/a')} ({d.get('source', 'unknown')})]\n{d.get('summary', '')}"
            for i, d in enumerate(summarized_docs)
            if d.get("summary")
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=conclusion_max_tokens + 1000,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant writing a formal research article with "
                        "three sections: Introduction, Body, and Conclusion. Do NOT write a "
                        "references section — that is handled separately.\n\n"
                        "The user's request may be in any language (e.g. Persian/Farsi). "
                        "Regardless of the input language, you MUST write the ENTIRE article "
                        "in ENGLISH ONLY — translate any non-English input as needed.\n\n"
                        "Use Markdown formatting throughout: **bold** the most important terms, "
                        "key findings, technical concepts, and critical numbers/results so a "
                        "reader can scan the article and immediately spot the key points. Do "
                        "not overdo it — bold only genuinely important words/phrases, not "
                        "entire sentences.\n\n"
                        "When the text includes mathematical formulas or equations, write them "
                        "using LaTeX syntax wrapped in $ for inline math (e.g. $\\alpha + \\beta$) "
                        "or $$ for standalone/block equations (e.g. $$L' = L + \\frac{\\partial L}{\\partial w} \\Delta w$$). "
                        "Do not use plain Unicode symbols like ∂, ∫, Δ for math — always use proper LaTeX commands.\n\n"
                        "Introduction: frame the user's research question/request and why it "
                        "matters, in a few paragraphs.\n\n"
                        "Body: synthesize the provided source summaries into ONE coherent, "
                        "integrated discussion — not a list of separate per-source summaries, "
                        "but a unified narrative connecting shared themes, agreements, and "
                        "contradictions across the sources.\n\n"
                        "Conclusion: a thorough, integrated synthesis of insights from ALL "
                        "sources combined, tailored specifically to the user's original "
                        f"request. This must be detailed and approximately {conclusion_max_tokens} "
                        "tokens long — the conclusion is the most important part of the article "
                        "and should not be brief, regardless of how short the Introduction or "
                        "Body are.\n\n"
                        "Format your response EXACTLY like this, with these exact headers:\n"
                        "## Introduction\n<content>\n\n## Body\n<content>\n\n## Conclusion\n<content>"

                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User's research request:\n{user_text}\n\n"
                        f"Source summaries:\n{combined_summaries}"
                    ),
                },
            ],
        )

        raw_text = response.choices[0].message.content
        sections = self._parse_sections(raw_text)
        sections["references"] = self.build_references(summarized_docs)
        return sections

    def _parse_sections(self, raw_text: str) -> Dict:
        """Split the model's raw output into introduction/body/conclusion parts."""
        sections = {"introduction": "", "body": "", "conclusion": ""}
        current = None

        for line in raw_text.splitlines():
            stripped = line.strip().lower()
            if stripped.startswith("## introduction"):
                current = "introduction"
                continue
            elif stripped.startswith("## body"):
                current = "body"
                continue
            elif stripped.startswith("## conclusion"):
                current = "conclusion"
                continue
            if current:
                sections[current] += line + "\n"

        for key in sections:
            sections[key] = sections[key].strip()

        return sections