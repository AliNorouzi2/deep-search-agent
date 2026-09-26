import re
import markdown as md_lib
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path


def load_css(file_path: str, base_dir: Path):
    """Load a CSS file and inject it into the page.
    base_dir should be the directory containing app.py (Path(__file__).resolve().parent).
    """
    css_path = base_dir / file_path
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_user_message(text: str):
    """Render the user's message as a styled chat bubble, auto-detecting
    RTL (Persian/Arabic) vs LTR (English) direction based on the text content.
    """
    has_rtl_chars = bool(re.search(r'[\u0600-\u06FF]', text))
    direction = "rtl" if has_rtl_chars else "ltr"
    text_align = "right" if has_rtl_chars else "left"

    st.markdown(
        f"""
        <div style="
            background-color: #f0f2f6;
            border-radius: 14px;
            padding: 10px 16px;
            margin: 8px 0;
            display: inline-block;
            max-width: 80%;
            direction: {direction};
            text-align: {text_align};
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_persian(text: str):
    """Render Persian text with RTL direction, Iran Sans font, and proper Markdown."""
    if not text or not text.strip():
        return

    text = re.sub(r"(</div>\s*)+$", "", text.strip())

    html_text = md_lib.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"]
    )

    st.markdown(
        f"""
        <div style="
            direction: rtl;
            text-align: right;
            unicode-bidi: isolate;
            font-family: 'IRANSans', 'IRANSansWeb', Tahoma, 'Segoe UI', sans-serif;
            line-height: 1.9;
            font-size: 15px;
        ">
            {html_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scroll_to_bottom_button():
    """Render a floating scroll-to-bottom button."""

    components.html(
        """
        <script>
        (function () {
            const parentDoc = window.parent.document;

            // Remove an old button if Streamlit recreated the iframe
            const oldButton = parentDoc.getElementById("scroll-to-bottom-btn");
            if (oldButton) {
                oldButton.remove();
            }

            // Create the button
            const btn = parentDoc.createElement("button");

            btn.id = "scroll-to-bottom-btn";
            btn.type = "button";
            btn.innerHTML = "&#8595;";

            // Button styling
            btn.style.cssText = `
                position: fixed;
                right: 25px;
                bottom: 90px;
                width: 46px;
                height: 46px;
                border-radius: 50%;
                border: none;
                background: #ffffff;
                color: #333333;
                box-shadow: 0 3px 12px rgba(0,0,0,0.20);
                font-size: 24px;
                cursor: pointer;
                z-index: 999999;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            `;

            parentDoc.body.appendChild(btn);


            // Find the actual scrollable element
            function findScrollContainer() {

                const candidates = [
                    parentDoc.querySelector('[data-testid="stAppViewContainer"]'),
                    parentDoc.querySelector('[data-testid="stMain"]'),
                    parentDoc.querySelector('section.main'),
                    parentDoc.documentElement,
                    parentDoc.body
                ];

                for (const element of candidates) {

                    if (!element) {
                        continue;
                    }

                    const style = parentDoc.defaultView.getComputedStyle(element);

                    const isScrollable =
                        element.scrollHeight > element.clientHeight &&
                        (
                            style.overflowY === "auto" ||
                            style.overflowY === "scroll" ||
                            element === parentDoc.documentElement ||
                            element === parentDoc.body
                        );

                    if (isScrollable) {
                        return element;
                    }
                }

                return null;
            }


            // Scroll to the bottom
            function scrollToBottom() {

                const container = findScrollContainer();

                if (container) {

                    container.scrollTo({
                        top: container.scrollHeight,
                        behavior: "smooth"
                    });

                    return;
                }


                // Fallback: scroll the window
                parentDoc.defaultView.scrollTo({
                    top: parentDoc.documentElement.scrollHeight,
                    behavior: "smooth"
                });

            }


            // Handle button click
            btn.addEventListener("click", function (event) {

                event.preventDefault();
                event.stopPropagation();

                scrollToBottom();

            });


            // Button hover effect
            btn.addEventListener("mouseenter", function () {
                btn.style.transform = "scale(1.08)";
                btn.style.boxShadow = "0 5px 16px rgba(0,0,0,0.25)";
            });

            btn.addEventListener("mouseleave", function () {
                btn.style.transform = "scale(1)";
                btn.style.boxShadow = "0 3px 12px rgba(0,0,0,0.20)";
            });

        })();


        // Handle button click
        btn.addEventListener("click", function (event) {
        
            event.preventDefault();
            event.stopPropagation();
        
            scrollToBottom();
        
        });
        </script>
        """,
        height=0,
    )

def render_scroll_to_last_turn_script():
    """Scroll to the bottom of the conversation once, when a new turn was just added."""
    components.html(
        """
        <script>
        function scrollToBottom() {
            const parentWindow = window.parent;
            const parentDocument = parentWindow.document;

            parentWindow.scrollTo({
                top: parentDocument.documentElement.scrollHeight,
                behavior: "smooth"
            });

            const appView = parentDocument.querySelector(
                '[data-testid="stAppViewContainer"]'
            );
            if (appView) {
                appView.scrollTo({
                    top: appView.scrollHeight,
                    behavior: "smooth"
                });
            }

            const bottom = parentDocument.getElementById("conversation-bottom");
            if (bottom) {
                bottom.scrollIntoView({ behavior: "smooth", block: "end" });
            }
        }

        setTimeout(scrollToBottom, 300);
        setTimeout(scrollToBottom, 800);
        setTimeout(scrollToBottom, 1500);
        </script>
        """,
        height=1
    )


def render_chat_bar_position_script():
    """Keep the chat bar, uploader panel, and options panel horizontally
    centered on the main content area (accounting for the sidebar width),
    and update their position whenever the sidebar is resized/toggled.
    """
    components.html(
        """
        <script>
            function updateChatBarPosition() {
                const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
                const sidebarWidth = sidebar ? sidebar.offsetWidth : 0;
                const mainAreaCenter = sidebarWidth + (window.parent.innerWidth - sidebarWidth) / 2;

                const chatBar = window.parent.document.querySelector('.st-key-chat_bar');
                if (chatBar) {
                    chatBar.style.left = mainAreaCenter + "px";
                    chatBar.style.transform = "translateX(-50%)";
                }

                const uploaderPanel = window.parent.document.querySelector('.st-key-uploader_panel');
                if (uploaderPanel) {
                    uploaderPanel.style.left = mainAreaCenter + "px";
                    uploaderPanel.style.transform = "translateX(-50%)";
                }

                const optionsPanel = window.parent.document.querySelector('.st-key-options_panel');
                if (optionsPanel && chatBar) {
                    const chatBarRect = chatBar.getBoundingClientRect();
                    optionsPanel.style.left = chatBarRect.left + "px";
                    optionsPanel.style.transform = "none";
                }
            }

            window.parent.addEventListener('resize', updateChatBarPosition);
            const observer = new MutationObserver(updateChatBarPosition);
            const sidebarEl = window.parent.document.querySelector('[data-testid="stSidebar"]');
            if (sidebarEl) {
                observer.observe(sidebarEl, { attributes: true, attributeFilter: ['style', 'class'] });
            }
            setTimeout(updateChatBarPosition, 300);
            setInterval(updateChatBarPosition, 1000);
        </script>
        """,
        height=0
    )