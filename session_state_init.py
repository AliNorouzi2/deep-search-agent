import streamlit as st
from agents.history_store import HistoryStore


def init_session_state(history_store: HistoryStore):
    """Initialize all session state variables used across the app.
    Must be called once at the top of main(), before anything else
    reads from st.session_state.
    """
    defaults = {
        "show_uploader": False,
        "uploaded_registry": {},  # key: file_name, value: file_path
        "file_paths": [],
        "run_analysis": False,
        "show_history": True,
        "effort_level": "Low",
        "is_analyzing": False,
        "pending_text": "",
        "current_query": "",
        "scroll_to_turn_id": None,
        "conversation": [],  # list of turns; each: user_text, mode, article, result, papers, answer
        "analysis_thread": None,
        "analysis_boxes": None,
        "current_conversation_id": None,
        "show_options_menu": False,
        "use_web_search": True,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # "history" needs special handling since its default comes from a function call
    if "history" not in st.session_state:
        st.session_state.history = history_store.load()