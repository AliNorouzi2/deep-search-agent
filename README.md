# 🤖 AI Agent Deep Search

<div align="center">

**A multi-agent research assistant that finds, analyzes, and synthesizes academic papers into a polished research article — with follow-up Q&A, Persian translation, and audio playback.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.63-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## ✨ What It Does

Type a research question, and a pipeline of specialized AI agents:

1. 🧭 **Plans** which academic source (arXiv, Semantic Scholar, PubMed) best fits your topic
2. 🔑 **Extracts** English search keywords — even if you asked in Persian
3. 🌐 **Searches & downloads** the most relevant open-access papers
4. 📄 **Analyzes** every PDF (yours and the fetched ones) in detail
5. ✍️ **Writes** a full article — Introduction, Body, Conclusion, References
6. 💬 **Keeps the conversation going** — ask follow-ups, request edits, or dig deeper
7. 🔊🌍 **Reads it aloud** or **translates it to Persian** on demand

All results are saved to a **persistent chat history** (browser local storage) so nothing is lost on refresh.

---

## 🖥️ Preview

> A chat-style interface: type your question, watch the agents work, and read a fully-formatted research article — right in your browser.

---

## 🧩 Tech Stack

| Category | Technology |
|---|---|
| **UI / Frontend** | [Streamlit](https://streamlit.io/) (custom CSS + injected JS for a fixed chat bar & floating panels) |
| **LLM Runtime** | [Ollama](https://ollama.com/) (local models — `llama3.2`, `qwen2.5`, etc.) via the `openai` Python SDK |
| **Academic Search** | arXiv API · Semantic Scholar Graph API · PubMed (NCBI E-utilities) |
| **PDF Parsing** | `pypdf` |
| **Translation (EN → FA)** | [Argos Translate](https://www.argosopentech.com/) — fully offline |
| **Text-to-Speech** | `gTTS` (Google Text-to-Speech) |
| **Markdown Rendering (FA)** | `markdown` + custom RTL styling |
| **Persistence** | `streamlit-local-storage` (browser-side chat history) |
| **Env Config** | `python-dotenv` |
| **HTTP** | `requests` |

---

## 🏗️ Architecture

The app is split into focused, single-purpose agents — each one a small class with a clear job:

```
app.py                     → Streamlit UI orchestration & the analysis pipeline
├── agents/
│   ├── Planner.py          → picks the best paper source (arXiv / Semantic Scholar / PubMed)
│   ├── key_word.py          → extracts English keywords + filters papers for relevance
│   ├── Document_collector.py→ searches & downloads real PDFs (with redirect/HTML detection)
│   ├── User_docs.py         → extracts text from PDFs & runs per-document analysis
│   ├── File_analyser.py     → summarizes documents (Docs class)
│   ├── Output_design.py     → writes the final Introduction/Body/Conclusion article
│   ├── text_input.py        → classifies a new message as follow-up vs. new analysis
│   ├── AI_ask.py             → answers follow-ups / edits the article using existing context
│   ├── translator.py        → offline English → Persian translation (Argos)
│   ├── history_store.py     → reads/writes chat history to browser local storage
│   └── upload_manager.py    → handles user PDF uploads (dedupe, limits, cleanup)
├── ui/
│   └── components.py        → reusable render functions (chat bubbles, scroll button, RTL text)
├── session_state_init.py    → centralizes all Streamlit session-state defaults
├── config.py                → effort-level settings (Low / Medium / High)
└── static/style.css         → all custom styling (fixed chat bar, panels, buttons)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12+
- [Ollama](https://ollama.com/) installed and running locally, with at least one model pulled:
  ```bash
  ollama pull llama3.2
  ```

### 2. Install dependencies
```bash
pip install streamlit streamlit-option-menu streamlit-local-storage openai requests python-dotenv pypdf gTTS markdown argostranslate
```

### 3. Configure environment variables
Create a `.env` file in the project root:
```env
SEMANTIC_SCHOLAR_API_KEY=your_key_here
```
*(Get a free key at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) — the app falls back to arXiv automatically if this is missing or the request fails.)*

### 4. Run the app
```bash
streamlit run app.py
```

---

## 🎛️ Features at a Glance

- ⚡ **Effort levels** (Low / Medium / High) — control how deep and long each analysis goes
- 🌐 **Toggle web search** — use only your uploaded PDFs if you prefer
- 📎 **Upload up to 5 PDFs** — auto-deduplicated by filename
- 🧠 **Smart follow-ups** — the app tells apart "explain more" from "start a new topic"
- 🗂️ **Persistent history sidebar** — revisit or delete past conversations
- 🔊 **Listen** to any result, 🌍 **translate** it to Persian with proper RTL rendering

---

## 📌 Notes

- All LLM calls run against a **local Ollama server** — no data leaves your machine for the analysis/writing steps.
- Translation runs fully **offline** via Argos Translate.
- Only the academic-search step (arXiv / Semantic Scholar / PubMed) requires internet access.

</div>
