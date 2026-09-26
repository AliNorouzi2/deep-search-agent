import streamlit as st
from streamlit_option_menu import option_menu
from pathlib import Path
import asyncio
import uuid
from gtts import gTTS
from io import BytesIO
import threading
import time
from datetime import datetime
from utils.logger import setup_logger
from utils.exceptions import ResumeProcessingError
from agents.File_analyser import Docs
from agents.User_docs import UserDocs
from agents.key_word import KeywordExtractor
from agents.Document_collector import DocumentCollector
from agents.translator import Translator
from agents.Output_design import OutputDesigner
from agents.Planner import Planner
from agents.text_input import IntentClassifier
from agents.AI_ask import AIAsk
from agents.history_store import HistoryStore
from agents.upload_manager import UploadManager
from session_state_init import init_session_state
from ui.components import load_css, render_user_message, render_persian, render_scroll_to_bottom_button, render_scroll_to_last_turn_script, render_chat_bar_position_script
from config import EFFORT_SETTINGS

# Configure Streamlit page
st.set_page_config(
    page_title="AI Agent Deep search",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

logger = setup_logger()
upload_manager = UploadManager()
history_store = HistoryStore()

# CSS
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 10px;">
        <svg width="40" height="40" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="26" cy="26" r="18" stroke="#1a1a1a" stroke-width="3"/>
            <path d="M39 39L54 54" stroke="#1a1a1a" stroke-width="4" stroke-linecap="round"/>
            <circle cx="26" cy="26" r="3" fill="#1a1a1a"/>
            <circle cx="18" cy="20" r="2" fill="#1a1a1a"/>
            <circle cx="34" cy="20" r="2" fill="#1a1a1a"/>
            <circle cx="18" cy="32" r="2" fill="#1a1a1a"/>
            <circle cx="34" cy="32" r="2" fill="#1a1a1a"/>
            <line x1="26" y1="26" x2="18" y2="20" stroke="#1a1a1a" stroke-width="1.5"/>
            <line x1="26" y1="26" x2="34" y2="20" stroke="#1a1a1a" stroke-width="1.5"/>
            <line x1="26" y1="26" x2="18" y2="32" stroke="#1a1a1a" stroke-width="1.5"/>
            <line x1="26" y1="26" x2="34" y2="32" stroke="#1a1a1a" stroke-width="1.5"/>
        </svg>
        <h1 style="margin: 0;">Deep research</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

load_css("static/style.css", Path(__file__).resolve().parent)


def main():
    init_session_state(history_store)

    if st.session_state.show_history:
        with st.sidebar:
            st.subheader("History")

            if not st.session_state.history:
                st.caption("No analyses yet.")

            for entry in reversed(st.session_state.history):
                col_title, col_delete = st.columns([5, 1])
                with col_title:
                    if st.button(entry["title"], key=f"load_{entry['id']}", use_container_width=True):
                        st.session_state.conversation = entry.get("conversation", [])
                        st.session_state.current_conversation_id = entry["id"]
                        st.rerun()

                with col_delete:
                    if st.button("", icon=":material/delete:", key=f"delete_{entry['id']}"):
                        st.session_state.history = history_store.delete_entry(st.session_state.history, entry["id"])
                        history_store.save(st.session_state.history)
                        time.sleep(0.5)
                        st.rerun()
                        
    else:
        if st.button("", icon=":material/menu:", key="open_history_btn", help="Show history"):
            st.session_state.show_history = True
            st.rerun()

    with st.container(key="chat_bar"):
        col_options, col1, col2, col3, col4 = st.columns([0.6, 12, 0.6, 0.6, 1.2], gap="small")
        with col_options:
            if st.button("", icon=":material/add:", help="Options", key="options_button", disabled=st.session_state.is_analyzing):
                st.session_state.show_options_menu = not st.session_state.show_options_menu
        with col1:
            user_text = st.text_input(
                "Message", 
                placeholder="Type your message...", 
                label_visibility="collapsed", 
                disabled=st.session_state.is_analyzing,
            )
        with col2:
            if st.button("", icon=":material/attach_file:", help="Attach PDF files", key="upload_button", disabled=st.session_state.is_analyzing,):
                st.session_state.show_uploader = not st.session_state.show_uploader
        with col3:
            if st.button("", icon=":material/arrow_forward:", help="Start analysis", key="analyze_button", disabled=st.session_state.is_analyzing,):
                st.session_state.run_analysis = True
        with col4:
            st.session_state.effort_level = st.selectbox(
                "Effort", ["Low", "Medium", "High"],
                index=["Low", "Medium", "High"].index(st.session_state.effort_level),
                label_visibility="collapsed",
                key="effort_selectbox",
                disabled=st.session_state.is_analyzing,
            )

    # Options panel — positioned right above the chat bar, similar to the uploader panel
    if st.session_state.show_options_menu:
        with st.container(key="options_panel"):
            st.session_state.use_web_search = st.checkbox(
                "Use online papers (arXiv, Semantic Scholar, PubMed)",
                value=st.session_state.use_web_search,
                key="use_web_search_checkbox",
            )

    # Uploader panel — positioned right above the chat bar via CSS
    if st.session_state.show_uploader:
        with st.container(key="uploader_panel"):
            uploaded_files = st.file_uploader(
                "Choose PDF files (up to 5)",
                type=["pdf"],
                accept_multiple_files=True,
                help="Upload up to 5 PDFs to analyze",
                label_visibility="visible",
            )
    else:
        uploaded_files = None

    if uploaded_files:
        result = upload_manager.process_uploads(uploaded_files, st.session_state.uploaded_registry)

        if result["was_truncated"]:
            st.warning(f"You can upload up to {upload_manager.max_files} files only. Only the first {upload_manager.max_files} will be processed.")

        if result["skipped_names"]:
            st.caption(f"Ignored {len(result['skipped_names'])} duplicate file(s): {', '.join(set(result['skipped_names']))}")

        progress_bar = st.progress(0)
        total = len(result["processed"]) + len(result["errors"])

        for idx, item in enumerate(result["processed"]):
            st.info(f"{item['name']} uploaded successfully!")
            progress_bar.progress((idx + 1) / total if total else 1.0)

        for item in result["errors"]:
            st.error(f"Error handling file upload for {item['name']}: {item['error']}")
            logger.error(f"Upload error for {item['name']}: {item['error']}")

        st.session_state.file_paths = result["file_paths"]

    render_conversation()
    render_scroll_to_bottom_button()

    if st.session_state.get("scroll_to_turn_id"):
        render_scroll_to_last_turn_script()

    st.session_state.scroll_to_turn_id = None
    
    # Analyse 1...
    if st.session_state.run_analysis and user_text and not st.session_state.is_analyzing:
        st.session_state.run_analysis = False

        if st.session_state.conversation:
            last_turn = st.session_state.conversation[-1]
            intent_agent = IntentClassifier()
            mode = intent_agent.classify_intent(user_text, last_turn["user_text"])
        else:
            mode = "new_analysis"

        st.session_state.is_analyzing = True
        st.session_state.pending_text = user_text
        st.session_state.pending_mode = mode
        st.session_state.analysis_thread = None
        st.session_state.analysis_boxes = None
        st.rerun()

    # Analyse 2...
    if st.session_state.is_analyzing:
        print("-- Start Analyse...")
        analysis_text = st.session_state.pending_text
        mode = st.session_state.pending_mode

        # --- Start the background thread once ---
        if st.session_state.analysis_thread is None:
            boxes = {
                "analysis_result": {},
                "analysis_error": {},
                "article_result": {},
                "papers": [],
                "title": None,
                "start_time": time.time(),
            }

            if mode == "follow_up":
                print(f"[app] Using EXISTING data (follow_up) for: '{analysis_text[:50]}...'")
                last_turn = st.session_state.conversation[-1]
                conversation_snapshot = list(st.session_state.conversation)

                def run_follow_up():
                    try:
                        ai_ask_agent = AIAsk()
                        boxes["analysis_result"]["value"] = ai_ask_agent.respond(
                            user_text=analysis_text,
                            article=last_turn["article"],
                            individual_summaries=last_turn["result"]["individual_summaries"],
                            conversation_history=conversation_snapshot,
                        )
                    except Exception as e:
                        boxes["analysis_error"]["value"] = e

                thread = threading.Thread(target=run_follow_up)

            else:
                print(f"[app] Starting FULL NEW analysis for: '{analysis_text[:50]}...'")
                docs_agent = Docs()
                user_docs_agent = UserDocs()
                keyword_agent = KeywordExtractor()
                collector_agent = DocumentCollector()
                output_designer_agent = OutputDesigner()
                planner_agent = Planner()

                user_file_paths = st.session_state.file_paths
                effort = EFFORT_SETTINGS[st.session_state.effort_level]
                use_web_search = st.session_state.use_web_search

                def run_new_analysis():
                    try:
                        if use_web_search:
                            source = planner_agent.select_source(analysis_text)
                            keywords = keyword_agent.extract_keywords(analysis_text)
                            candidate_papers = collector_agent.search_by_keywords(
                                keywords, source=source, candidate_pool=20
                            )
                            papers = keyword_agent.filter_relevant_papers(
                                analysis_text, candidate_papers, max_results=3
                            )
                            agent_file_paths = collector_agent.download_papers(papers)
                        else:
                            papers = []
                            agent_file_paths = []
                        
                        boxes["papers"] = papers

                        user_analyses = (
                            user_docs_agent.analyze_pdfs(
                                user_file_paths,
                                max_tokens=effort["max_tokens"],
                                max_input_chars=effort["max_input_chars"],
                            ) if user_file_paths else []
                        )
                        agent_analyses = (
                            user_docs_agent.analyze_pdfs(
                                agent_file_paths,
                                max_tokens=effort["max_tokens"],
                                max_input_chars=effort["max_input_chars"],
                            ) if agent_file_paths else []
                        )
                        for analysis, paper in zip(agent_analyses, papers):
                            analysis["pdf_url"] = paper.get("pdf_url")

                        if not user_analyses and not agent_analyses:
                            boxes["analysis_error"]["value"] = ValueError(
                                "No documents were available to analyze — you didn't upload "
                                "any files, and no relevant papers were found online for "
                                "this topic."
                            )
                            return

                        boxes["analysis_result"]["value"] = docs_agent.process(
                            user_pdfs=user_analyses,
                            agent_pdfs=agent_analyses,
                            max_tokens=effort["max_tokens"],
                            max_input_chars=effort["max_input_chars"],
                        )

                        boxes["article_result"]["value"] = output_designer_agent.generate_article(
                            user_text=analysis_text,
                            summarized_docs=boxes["analysis_result"]["value"]["individual_summaries"],
                            conclusion_max_tokens=effort["max_tokens"],
                        )

                        boxes["title"] = docs_agent.generate_title(analysis_text)
                    except Exception as e:
                        boxes["analysis_error"]["value"] = e

                thread = threading.Thread(target=run_new_analysis)

            thread.start()
            st.session_state.analysis_thread = thread
            st.session_state.analysis_boxes = boxes

        # --- Wait for the thread to finish (blocking, no rerun/Stop needed) ---
        thread = st.session_state.analysis_thread
        boxes = st.session_state.analysis_boxes

        status_label = "Answering..." if mode == "follow_up" else "Analyzing documents..."
        timer_placeholder = st.empty()

        with st.spinner(" "):  # spinner icon only, no separate text
            while thread.is_alive():
                elapsed = int(time.time() - boxes["start_time"])
                timer_placeholder.text(f"{status_label} {elapsed}s")
                time.sleep(0.5)

            thread.join()
            elapsed = int(time.time() - boxes["start_time"])
            timer_placeholder.text(f"{status_label} Finished in {elapsed}s")

        if "value" in boxes["analysis_error"]:
            st.warning(str(boxes["analysis_error"]["value"]))
        else:
            turn = {
                "id": str(uuid.uuid4()),
                "user_text": analysis_text,
                "mode": mode,
            }

            if mode == "follow_up":
                response = boxes["analysis_result"]["value"]
                last_turn = st.session_state.conversation[-1]
                if response["mode"] == "edit":
                    turn["article"] = {
                        "introduction": response["introduction"],
                        "body": response["body"],
                        "conclusion": response["conclusion"],
                        "references": last_turn["article"]["references"],
                    }
                    turn["result"] = last_turn["result"]
                    turn["papers"] = last_turn["papers"]
                else:
                    turn["answer"] = response["answer"]
                    turn["article"] = last_turn["article"]
                    turn["result"] = last_turn["result"]
                    turn["papers"] = last_turn["papers"]
            else:
                turn["article"] = boxes["article_result"]["value"]
                turn["result"] = boxes["analysis_result"]["value"]
                turn["papers"] = boxes["papers"]
                turn["title"] = boxes["title"]

            st.session_state.conversation.append(turn)
            st.session_state.scroll_to_turn_id = turn["id"]

            if mode == "new_analysis":
                conversation_id = str(uuid.uuid4())
                st.session_state.current_conversation_id = conversation_id
            else:
                conversation_id = st.session_state.current_conversation_id

            print(f"[DEBUG] mode={mode}, conversation_id={conversation_id}, existing_ids={[e['id'] for e in st.session_state.history]}")

            st.session_state.history = history_store.upsert_conversation(
                st.session_state.history,
                conversation_id=conversation_id,
                title=boxes.get("title"),
                conversation=st.session_state.conversation,
            )
            history_store.save(st.session_state.history)

            # cleanup
            try:
                upload_manager.cleanup(st.session_state.uploaded_registry)
                st.session_state.file_paths = []
            except Exception as e:
                st.error(f"Error cleaning up upload directory: {str(e)}")
                logger.error(f"Cleanup error: {str(e)}", exc_info=True)
                

        st.session_state.is_analyzing = False
        st.session_state.analysis_thread = None
        st.session_state.analysis_boxes = None
        time.sleep(0.5)
        st.rerun()


    render_chat_bar_position_script()

# Result
def render_conversation():
    for idx, turn in enumerate(st.session_state.conversation):
        st.markdown(f'<div id="turn-{turn["id"]}"></div>', unsafe_allow_html=True)
        render_user_message(turn['user_text'])

        if turn["mode"] == "follow_up" and "answer" in turn:
            st.markdown(turn["answer"])
            col_audio, col_translate = st.columns([1, 1])
            with col_audio:
                if st.button("", icon=":material/volume_up:", key=f"tts_answer_{idx}_{turn['id']}"):
                    with st.spinner("Generating audio..."):
                        try:
                            tts = gTTS(text=turn["answer"], lang="en")
                            audio_buffer = BytesIO()
                            tts.write_to_fp(audio_buffer)
                            audio_buffer.seek(0)
                            st.session_state[f"tts_audio_{turn['id']}"] = audio_buffer.read()
                        except Exception as e:
                            st.error(f"Error generating audio: {str(e)}")
            with col_translate:
                if st.button("", icon=":material/translate:", key=f"translate_answer_{idx}_{turn['id']}"):
                    with st.spinner("Translating..."):
                        try:
                            translator_agent = Translator()
                            st.session_state[f"translated_{turn['id']}"] = translator_agent.translate_to_persian(turn["answer"])
                        except Exception as e:
                            import traceback
                            st.error(f"Error translating text: {str(e)}")
                            st.code(traceback.format_exc())
            if f"tts_audio_{turn['id']}" in st.session_state:
                st.audio(st.session_state[f"tts_audio_{turn['id']}"], format="audio/mp3")
            if f"translated_{turn['id']}" in st.session_state:
                st.markdown("---")
                render_persian(st.session_state[f"translated_{turn['id']}"])
                st.divider()
            continue

        article = turn["article"]
        result = turn["result"]
        papers = turn["papers"]

        tab1, tab2, tab3 = st.tabs(["Final result", "Analysis Doc", "Web"])

        with tab1:
            st.subheader("Introduction")
            st.markdown(article["introduction"])
            st.subheader("Body")
            st.markdown(article["body"])
            st.subheader("Conclusion")
            st.markdown(article["conclusion"])
            st.subheader("References")
            for ref in article["references"]:
                st.markdown(f"- {ref}")

            full_text = article["introduction"] + "\n\n" + article["body"] + "\n\n" + article["conclusion"]

            col_audio, col_translate = st.columns([1, 1])
            with col_audio:
                if st.button("", icon=":material/volume_up:", key=f"tts_article_{idx}_{turn['id']}"):
                    with st.spinner("Generating audio..."):
                        try:
                            tts = gTTS(text=full_text, lang="en")
                            audio_buffer = BytesIO()
                            tts.write_to_fp(audio_buffer)
                            audio_buffer.seek(0)
                            st.session_state[f"tts_audio_{turn['id']}"] = audio_buffer.read()
                        except Exception as e:
                            st.error(f"Error generating audio: {str(e)}")
            with col_translate:
                if st.button("", icon=":material/translate:", key=f"translate_article_{idx}_{turn['id']}"):
                    with st.spinner("Translating..."):
                        try:
                            translator_agent = Translator()
                            st.session_state[f"translated_{turn['id']}"] = translator_agent.translate_to_persian(full_text)
                        except Exception as e:
                            st.error(f"Error translating text: {str(e)}")
            if f"tts_audio_{turn['id']}" in st.session_state:
                st.audio(st.session_state[f"tts_audio_{turn['id']}"], format="audio/mp3")
            if f"translated_{turn['id']}" in st.session_state:
                st.markdown("---")
                render_persian(st.session_state[f"translated_{turn['id']}"])
            st.divider()
            continue

        with tab2:
            for item in result["individual_summaries"]:
                if item.get("source") != "user_upload":
                    continue
                st.markdown(f"**{item.get('file_path')}**")
                st.write(item.get("summary"))

        with tab3:
            for paper in papers:
                st.markdown(f"**{paper['title']}**")
                st.write(paper["summary"])
                if paper.get("pdf_url"):
                    st.link_button("Open PDF", paper["pdf_url"], icon=":material/open_in_new:", key=f"pdf_{turn['id']}_{paper['title'][:20]}")


        st.divider()

    # Anchor for auto-scroll
    st.markdown(
        '<div id="conversation-bottom"></div>',
        unsafe_allow_html=True
    ) 
    

if __name__ == "__main__":
    main()