"""Trochiá — AI Chat page."""
import sys, os
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from chatbot import get_response, is_ai_enabled

SUGGESTIONS = [
    "What does a RED signal mean?",
    "How are prices forecasted?",
    "When should I pre-buy?",
    "How accurate are the models?",
    "What data sources do you use?",
]


def render():
    st.markdown('<div class="sec-header">AI Chat</div>', unsafe_allow_html=True)

    ai_on = is_ai_enabled()
    if ai_on:
        st.markdown('<p style="color:#8BA0B0;font-size:0.85rem;">Powered by Claude. Ask anything about your commodity data.</p>',
                    unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="font-size:0.84rem;">
            Running in FAQ mode. To enable full AI responses, add ANTHROPIC_API_KEY to your .env file.
        </div>
        """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if not st.session_state.chat_messages:
        st.markdown('<p style="color:#8BA0B0;font-size:0.82rem;margin-bottom:0.5rem;">Try asking:</p>',
                    unsafe_allow_html=True)
        cols = st.columns(len(SUGGESTIONS))
        for col, q in zip(cols, SUGGESTIONS):
            with col:
                if st.button(q, use_container_width=True, key=f"sugg_{q}"):
                    _send(q)
                    st.rerun()

    user_input = st.chat_input("Ask a question about Trochiá or your commodity data...")
    if user_input:
        _send(user_input)
        st.rerun()


def _send(message: str):
    st.session_state.chat_messages.append({"role": "user", "content": message})
    reply = get_response(message, st.session_state.chat_history)
    st.session_state.chat_history.append({"role": "user", "content": message})
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
