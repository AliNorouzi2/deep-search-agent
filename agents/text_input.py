from openai import OpenAI


class IntentClassifier:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def classify_intent(self, user_text: str, previous_user_text: str) -> str:
        """Determine whether the new message is a follow-up to the previous
        analysis (a question, correction, or edit request) or a request for
        a brand new, unrelated analysis.

        Returns 'follow_up' or 'new_analysis'.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=10,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify whether a user's new message is a FOLLOW_UP to "
                        "their previous research request, or a completely NEW_ANALYSIS "
                        "request unrelated to it.\n\n"
                        "IMPORTANT: In about 80% of real cases, the correct answer is "
                        "FOLLOW_UP. Treat FOLLOW_UP as the overwhelming default. Only "
                        "answer NEW_ANALYSIS in the rare case where the new message is "
                        "about a COMPLETELY different, unrelated subject — as different "
                        "as, for example, 'AI in healthcare' vs 'ancient Roman history' or user ask you to use more article and resources. "
                        "If there is ANY plausible connection, overlap, or shared theme "
                        "between the two messages, you MUST answer FOLLOW_UP.\n\n"
                        "ALWAYS classify these as FOLLOW_UP, regardless of how short or "
                        "vague they are:\n"
                        "- Requests to explain more, expand, elaborate, clarify, go deeper, "
                        "simplify, shorten, summarize, rephrase, translate, or fix something\n"
                        "- Any question containing words like 'more', 'why', 'how', 'what "
                        "about', 'explain', 'detail', 'example'\n"
                        "- Short reactions or follow-up questions that reference the "
                        "previous topic even implicitly (e.g. same keywords, pronouns like "
                        "'it', 'that', 'this')\n"
                        "- Messages that repeat or overlap with words from the previous "
                        "request, even with additions like '(explain more)'\n\n"
                        "Examples:\n"
                        "Previous: 'AI in healthcare' | New: 'ai (explain more)' -> FOLLOW_UP\n"
                        "Previous: 'AI in healthcare' | New: 'can you elaborate on that' -> FOLLOW_UP\n"
                        "Previous: 'AI in healthcare' | New: 'medieval European trade routes' -> NEW_ANALYSIS\n\n"
                        "Previous: 'AI-Agent' | New: 'Use more article or docs for explane more' -> NEW_ANALYSIS\n\n"
                        "- Requests to use more resources, use more article, use different articles, "
                        "means that user want new_analysis\n"
                        "Respond with ONLY one word: follow_up or new_analysis."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Previous request:\n{previous_user_text}\n\n"
                        f"New message:\n{user_text}"
                    ),
                },
            ],
        )

        choice = response.choices[0].message.content.strip().lower()
        if choice not in ("follow_up", "new_analysis"):
            choice = "follow_up"  # bias the fallback toward follow_up too

        print(f"[IntentClassifier] Previous: '{previous_user_text[:50]}...' | New: '{user_text[:50]}...' -> {choice}")
        return choice