import streamlit as st
import database.database as db
from llm.llm_client import execute_completion
from llm.prompts import SYSTEM_CHAT_PROMPT
from rag.parser import parse_file
from rag.rag_engine import retrieve_rag_context
from ui.styles import apply_gemini_theme

# Initialize Database & UI Theme
db.init_db()

st.set_page_config(
    page_title="Gemini AI Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_gemini_theme()

# Session State Setup
if "active_thread" not in st.session_state:
    threads = db.fetch_all_threads()
    st.session_state.active_thread = threads[0] if threads else "Default Chat"

# --- SIDEBAR (Gemini Mobile Drawer) ---
with st.sidebar:
    st.title("✨ Gemini Studio")
    
    api_key = st.text_input("OpenRouter API Key", type="password", value=st.secrets.get("OPENROUTER_API_KEY", ""))
    
    st.divider()
    
    col_t1, col_t2 = st.columns([3, 1])
    col_t1.subheader("Recent Chats")
    if col_t2.button("➕", key="btn_new_thread"):
        new_title = f"Chat {len(db.fetch_all_threads()) + 1}"
        db.create_thread(new_title)
        st.session_state.active_thread = new_title
        st.rerun()

    # Threads render with latest updated on top
    all_threads = db.fetch_all_threads()
    for thread_name in all_threads:
        c_btn, c_del = st.columns([4, 1])
        is_active = thread_name == st.session_state.active_thread
        prefix = "👉 " if is_active else "💬 "
        
        if c_btn.button(f"{prefix}{thread_name}", key=f"th_{thread_name}"):
            st.session_state.active_thread = thread_name
            st.rerun()
            
        if len(all_threads) > 1:
            if c_del.button("🗑️", key=f"del_{thread_name}"):
                db.delete_thread(thread_name)
                st.session_state.active_thread = db.fetch_all_threads()[0]
                st.rerun()

# --- MAIN VIEW ---
st.title(f"💬 {st.session_state.active_thread}")

# Load active thread history from SQLite
messages = db.fetch_thread_messages(st.session_state.active_thread)
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# File Attachments
uploaded_files = st.file_uploader("Attach Context Sources", type=["pdf", "docx", "csv", "xlsx"], accept_multiple_files=True)
parsed_docs = [parse_file(f) for f in uploaded_files] if uploaded_files else []

# User Input
user_input = st.chat_input("Ask anything or submit study notes...")
if user_input:
    if not api_key:
        st.error("Please enter your OpenRouter API Key in the sidebar.")
    else:
        # Save user query to SQLite
        db.add_chat_message(st.session_state.active_thread, "user", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        # Retrieve RAG context if sources attached
        rag_context = retrieve_rag_context(parsed_docs, user_input) if parsed_docs else ""
        
        # Build prompt payload
        prompt_payload = [SYSTEM_CHAT_PROMPT]
        if rag_context:
            prompt_payload.append({"role": "system", "content": f"Relevant Study Context:\n{rag_context}"})
            
        for m in messages:
            prompt_payload.append({"role": m["role"], "content": m["content"]})
        prompt_payload.append({"role": "user", "content": user_input})

        # Query OpenRouter with fallback
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response_text, used_model = execute_completion(api_key, prompt_payload)
                    st.markdown(response_text)
                    db.add_chat_message(st.session_state.active_thread, "assistant", response_text)
                    st.rerun()
                except Exception as ex:
                    st.error(str(ex))
