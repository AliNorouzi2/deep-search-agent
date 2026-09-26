from openai import OpenAI


SOURCE_OPTIONS = ["arxiv", "semantic_scholar", "pubmed"]


class Planner:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)  # key unused by Ollama

    def select_source(self, user_text: str) -> str:
        """Determine the best academic search source for the user's topic.

        Returns one of: 'arxiv', 'semantic_scholar', 'pubmed'.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=10,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify a research request into the best academic search "
                        "source to query. The user's input may be in any language.\n\n"
                        "Choose exactly one of these options:\n"
                        "- 'arxiv': for computer science, AI/ML, AI-Agents, physics, mathematics, "
                        "statistics topics.\n"
                        "- 'pubmed': for biology, medicine, health, clinical, life sciences "
                        "topics.\n"
                        "- 'semantic_scholar': for everything else, or when the topic spans "
                        "multiple fields, or general/broad academic topics (social science, "
                        "economics, humanities, engineering, etc.).\n\n"
                        "Respond with ONLY one word: arxiv, pubmed, or semantic_scholar. "
                        "No explanation, no punctuation."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Classify this research request:\n\n{user_text}",
                },
            ],
        )

        choice = response.choices[0].message.content.strip().lower()
        if choice not in SOURCE_OPTIONS:
            print(f"[Planner] Model returned invalid choice '{choice}', falling back to semantic_scholar")
            choice = "semantic_scholar"  # safe fallback for broadest coverage

        print(f"Selected source: {choice}")
        return choice