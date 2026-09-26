from typing import List
from openai import OpenAI


class KeywordExtractor:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)  # key unused by Ollama

    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract the most relevant search keywords from user input text,
        suitable for querying academic search engines like arXiv.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract concise search keywords/phrases from user text, "
                        "to be used for searching academic paper databases like arXiv. "
                        "The user's input may be in any language (e.g. Persian/Farsi). "
                        "Regardless of the input language, you MUST translate the concepts "
                        "and respond with keywords in ENGLISH ONLY, since arXiv search only "
                        "works well with English terms. "
                        "Respond with ONLY a comma-separated list of English keywords, "
                        "nothing else — no numbering, no explanation, no non-English text."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Extract up to {max_keywords} keywords from this text:\n\n{text}",
                },
            ],
        )

        raw_output = response.choices[0].message.content
        keywords = [kw.strip() for kw in raw_output.split(",") if kw.strip()]
        print(keywords[:max_keywords])
        return keywords[:max_keywords]

    def filter_relevant_papers(
        self,
        user_text: str,
        papers: List[dict],
        max_results: int = 3,
    ) -> List[dict]:
        """Ask the LLM to judge each candidate paper's relevance to the user's
        stated interests, and keep only the ones it considers a good match.
        """
        relevant_papers = []

        for paper in papers:
            if len(relevant_papers) >= max_results:
                break

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You judge whether an academic paper is genuinely relevant to "
                            "what a user is interested in. Be strict: a paper only counts as "
                            "relevant if its actual topic overlaps with the user's stated "
                            "interests — a shared general term like 'machine learning' is NOT "
                            "enough on its own if the paper's actual domain/application is "
                            "unrelated (e.g. a biology validation paper is NOT relevant to "
                            "someone interested in AI agents and LLMs, even though both "
                            "mention 'machine learning').\n\n"
                            "Respond with ONLY one word: 'yes' or 'no'."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"User's interests:\n{user_text}\n\n"
                            f"Candidate paper title: {paper['title']}\n"
                            f"Candidate paper abstract: {paper['summary']}\n\n"
                            "Is this paper relevant to the user's interests?"
                        ),
                    },
                ],
            )

            verdict = response.choices[0].message.content.strip().lower()
            if verdict.startswith("yes"):
                relevant_papers.append(paper)

        print("# Selected papers:")
        for p in relevant_papers:
            print(f"- {p['title']}")

        return relevant_papers