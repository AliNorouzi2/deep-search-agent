from typing import Dict, List
from openai import OpenAI


class AIAsk:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def respond(self, user_text: str, article: Dict, individual_summaries: List[Dict], conversation_history: List[Dict]) -> Dict:
        """Respond to a follow-up message using the previous article, document
        summaries, and the full conversation history as context.
        """
        summaries_text = "\n\n---\n\n".join(
            f"[{d.get('file_path', 'n/a')}]\n{d.get('summary', '')}"
            for d in individual_summaries
            if d.get("summary")
        )

        history_text = "\n".join(
            f"User: {turn['user_text']}\nAssistant: {turn.get('answer', '(article was edited)')}"
            for turn in conversation_history
            if turn.get("mode") == "follow_up"
        )

        context = (
            f"Original article:\n\n"
            f"## Introduction\n{article.get('introduction', '')}\n\n"
            f"## Body\n{article.get('body', '')}\n\n"
            f"## Conclusion\n{article.get('conclusion', '')}\n\n"
            f"Source document summaries:\n{summaries_text}\n\n"
            f"Conversation so far:\n{history_text}"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=3000,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant continuing an ongoing conversation "
                        "about a previously generated research article. You do NOT have "
                        "access to the original source PDFs — you ONLY have the article "
                        "text, document summaries, and the conversation history given "
                        "below. Use ONLY this given context; do NOT search for new "
                        "sources, do NOT re-analyze from scratch, do NOT say things like "
                        "'let me analyze the documents' — you already have everything you "
                        "need right here.\n\n"
                        "Pay close attention to the conversation history — the user's new "
                        "message may be a short reply (like 'yes' or 'sure') that only "
                        "makes sense in light of what YOU just asked or said previously.\n\n"
                        "Decide whether the new message is:\n"
                        "1. A QUESTION about the article/sources — answer it directly using "
                        "ONLY the given context below.\n"
                        "2. An EDIT REQUEST — the user wants the article's Introduction, "
                        "Body, or Conclusion rewritten/expanded/shortened/corrected — "
                        "regenerate the FULL article (all three sections) using the SAME "
                        "underlying information already given below, incorporating the "
                        "requested change. Do not invent new source material.\n\n"
                        "Always respond in ENGLISH, using Markdown **bold** for key terms.\n\n"
                        "Format your response EXACTLY like one of these two forms:\n\n"
                        "For a question:\n"
                        "MODE: ANSWER\n<your answer>\n\n"
                        "For an edit request:\n"
                        "MODE: EDIT\n"
                        "## Introduction\n<content>\n\n## Body\n<content>\n\n## Conclusion\n<content>"
                    ),
                },
                {
                    "role": "user",
                    "content": f"{context}\n\n---\n\nUser's new follow-up message:\n{user_text}",
                },
            ],
        )

        raw_text = response.choices[0].message.content
        result = self._parse_response(raw_text)
        print(f"[AIAsk] Answered using existing context (mode={result['mode']}), no new documents fetched")
        return result

    def _parse_response(self, raw_text: str) -> Dict:
        lines = raw_text.splitlines()
        if not lines:
            return {"mode": "answer", "answer": raw_text}

        first_line = lines[0].strip().upper()

        if first_line.startswith("MODE: EDIT"):
            sections = {"introduction": "", "body": "", "conclusion": ""}
            current = None
            for line in lines[1:]:
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
            return {"mode": "edit", **sections}

        # MODE: ANSWER or unrecognized format — treat the rest as a plain answer
        answer_text = "\n".join(lines[1:]).strip() if first_line.startswith("MODE:") else raw_text
        return {"mode": "answer", "answer": answer_text}