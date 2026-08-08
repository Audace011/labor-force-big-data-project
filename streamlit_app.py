"""
Streamlit web app for the Labor Force AI Assistant (Section 4.5 + deployment
extra credit). Deployed for free on Streamlit Community Cloud.

Wraps the same ask() function from src/ai_assistant.py — no duplicated logic.
"""
import streamlit as st
from src.ai_assistant import ask

st.set_page_config(
    page_title="Labor Force AI Assistant",
    page_icon="📊",
    layout="centered",
)

st.title("📊 Global Labor Force Participation Rate — AI Assistant")
st.caption(
    "Ask a plain-English question about labor force participation rates "
    "(World Bank indicator SL.TLF.CACT.ZS, 1990–2025, 187 countries)."
)

with st.expander("Example questions"):
    st.markdown(
        """
        - What was Rwanda's participation rate in 2020?
        - Which country had the highest rate in 2025?
        - How has China's rate changed since 1990?
        - What is the average participation rate for the United States?
        """
    )

if "history" not in st.session_state:
    st.session_state.history = []

question = st.text_input("Your question:", placeholder="e.g. What was Rwanda's rate in 2020?")

col1, col2 = st.columns([1, 5])
with col1:
    ask_clicked = st.button("Ask", type="primary")

if ask_clicked and question.strip():
    with st.spinner("Thinking..."):
        answer = ask(question.strip())
    st.session_state.history.insert(0, (question.strip(), answer))

if st.session_state.history:
    st.divider()
    st.subheader("Conversation")
    for q, a in st.session_state.history:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**Assistant:** {a}")
        st.markdown("---")

st.caption(
    "Built for the Introduction to Big Data final project. "
    "Data source: World Bank Open Data. AI: Groq (Llama 3.3 70B)."
)
