from typing import List, Dict
from openai import OpenAI
import logging
logger = logging.getLogger(__name__)

class Docs:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)  # key unused by Ollama

    def combine_sources(
        self,
        user_pdfs: List[Dict],
        agent_pdfs: List[Dict],
    ) -> List[Dict]:
        """Combine PDFs uploaded by the user with PDFs fetched by the other agent
        into a single unified list, tagging each item with its origin.
        """
        combined: List[Dict] = []

        for doc in user_pdfs:
            combined.append({**doc, "source": "user_upload"})

        for doc in agent_pdfs:
            combined.append({**doc, "source": "external_agent"})

        return combined

    def summarize_document(self, text: str, max_tokens: int = 2000, max_input_chars: int = 15000) -> str:
        """Produce a detailed, research-grade summary of a single document's text."""
        truncated_text = text[:max_input_chars]

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant writing a detailed, technical summary "
                        "of an academic document, for a knowledgeable technical reader. "
                        "This should be long-form and specific — not a generic 3-sentence "
                        "summary. Cover, when applicable: the paper's core objective/problem, "
                        "its methodology (including key formulas, models, or algorithms), a "
                        "breakdown of its main sections/chapters, its key findings or "
                        "contributions, and any limitations mentioned. Be concrete and pull "
                        "real details from the text rather than writing vague generalities."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Write a detailed technical summary of this document:\n\n{truncated_text}",
                },
            ],
        )
        return response.choices[0].message.content

    def summarize_all(self, combined_docs: List[Dict], max_tokens: int = 2000, max_input_chars: int = 15000) -> List[Dict]:
        """Summarize each document in the combined list individually."""
        results: List[Dict] = []

        for doc in combined_docs:
            text = doc.get("analysis") or doc.get("text", "")
            try:
                summary = self.summarize_document(text, max_tokens, max_input_chars)
                results.append({**doc, "summary": summary})
            except Exception as e:
                results.append({**doc, "summary": None, "error": str(e)})

        return results

    def synthesize(self, summarized_docs: List[Dict], max_tokens: int = 2500) -> str:
        """Combine all individual summaries into one integrated analysis,
        highlighting overlaps, contradictions, and key insights across sources.
        """
        combined_text = "\n\n---\n\n".join(
            f"[Source: {d.get('source', 'unknown')} | File: {d.get('file_path', 'n/a')}]\n{d.get('summary', '')}"
            for d in summarized_docs
            if d.get("summary")
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant. You are given summaries of multiple "
                        "documents from different sources. Synthesize them into a single, "
                        "coherent analysis: identify common themes, note any contradictions "
                        "between sources, and highlight the most important insights overall."
                    ),
                },
                {
                    "role": "user",
                    "content": combined_text,
                },
            ],
        )
        return response.choices[0].message.content

    def process(self, user_pdfs: List[Dict], agent_pdfs: List[Dict], max_tokens: int = 2000, max_input_chars: int = 15000) -> Dict:
        """Combine and summarize each document individually. Does NOT synthesize
        a final_analysis — that's handled separately by OutputDesigner.
        """
        combined = self.combine_sources(user_pdfs, agent_pdfs)
        summarized = self.summarize_all(combined, max_tokens, max_input_chars)

        return {
            "individual_summaries": summarized,
        }

    def generate_title(self, user_text: str) -> str:
        """Generate a short, one-line title summarizing this analysis request."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=15,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate a very short, descriptive, one-line title "
                        "(strictly 3 to 4 words) for a research query, to be used as a "
                        "history label. "
                        "The user's input may be in any language (e.g. Persian/Farsi). "
                        "Regardless of the input language, you MUST respond with the title "
                        "in ENGLISH ONLY — translate if needed. "
                        "Respond with ONLY the title text — no quotes, no punctuation at the end, "
                        "no explanation, no non-English text."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Generate a 3-4 word English title for this research request (translate if needed):\n\n{user_text}",
                },
            ],
        )
        return response.choices[0].message.content.strip().strip('"')