"""Gemini Study Studio - Notebook-Centric Workspace Application Entrypoint."""

import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gemini Study Studio",
    page_icon="📓",
    layout="wide",
    initial_sidebar_state="expanded",
)

from analytics import get_dashboard_summary
from config import FALLBACK_MODELS
from database.database import get_db_connection, init_db
from database.notebooks import (
    create_notebook,
    delete_notebook,
    get_all_notebooks,
    get_notebook_notes,
    save_note,
)
from exam import (
    ExamTimer,
    generate_mcq_paper,
    generate_written_question_paper,
    grade_written_exam,
    score_mcq_submission,
)
from llm.llm_client import generate_response
from mistakes import generate_adaptive_revision_notes, get_due_mistakes, log_mistake, update_mistake_review
from rag import RAGEngine
from ui.styles import apply_gemini_theme

# Initialize Database Schema & UI
init_db()
apply_gemini_theme()

# Session State Initialization
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "active_exam" not in st.session_state:
    st.session_state.active_exam = None

if "exam_timer" not in st.session_state:
    st.session_state.exam_timer = None


# --- SIDEBAR: NOTEBOOK & MODEL MANAGEMENT ---

st.sidebar.title("📓 Notebook Manager")

# 1. API Key Input
api_key = st.sidebar.text_input(
    "OpenRouter API Key",
    type="password",
    value=os.getenv("OPENROUTER_API_KEY", ""),
    help="Required for LLM and RAG question generation.",
)

# 2. Model Target Selector
selected_model = st.sidebar.selectbox("LLM Model Target", options=FALLBACK_MODELS, index=0)

st.sidebar.divider()

# 3. Create New Notebook Modal/Form
st.sidebar.subheader("➕ Create Notebook")
with st.sidebar.form("create_notebook_form", clear_on_submit=True):
    new_nb_title = st.text_input("Notebook Title", placeholder="e.g., Natural Language Processing")
    new_nb_desc = st.text_area("Description", placeholder="Optional description...")
    btn_create_nb = st.form_submit_button("Create Workspace")

    if btn_create_nb:
        if new_nb_title.strip():
            try:
                nb_id = create_notebook(new_nb_title, new_nb_desc)
                st.sidebar.success(f"Notebook '{new_nb_title}' created!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error creating notebook: {e}")
        else:
            st.sidebar.warning("Please provide a notebook title.")

# 4. Notebook Selection & Deletion
all_notebooks = get_all_notebooks()

if not all_notebooks:
    st.sidebar.info("No notebooks found. Create one above to get started.")
    st.warning("⚠️ Please create or select a Notebook from the sidebar to begin.")
    st.stop()

nb_options = {f"{nb['title']} (ID: {nb['id']})": nb for nb in all_notebooks}
selected_nb_label = st.sidebar.selectbox("Active Notebook Workspace", options=list(nb_options.keys()))
active_notebook = nb_options[selected_nb_label]

col_nb_info, col_nb_del = st.sidebar.columns([0.8, 0.2])
col_nb_info.caption(f"Created: {active_notebook['created_at'][:10]}")

if col_nb_del.button("🗑️", help="Delete active notebook and all contents"):
    delete_notebook(active_notebook["id"])
    st.sidebar.success("Notebook deleted!")
    st.rerun()

st.sidebar.divider()

# 5. Multiple Sources Uploader for Active Notebook
st.sidebar.subheader("📄 Upload Notebook Sources")
uploaded_files = st.sidebar.file_uploader(
    f"Add sources to '{active_notebook['title']}'",
    type=["pdf", "docx", "pptx", "txt", "md", "csv", "xlsx", "png", "jpg", "jpeg", "json"],
    accept_multiple_files=True,
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        filename_tagged = f"[NB-{active_notebook['id']}] {uploaded_file.name}"
        if st.sidebar.button(f"Index {uploaded_file.name}", key=f"btn_{uploaded_file.name}"):
            with st.spinner(f"Indexing '{uploaded_file.name}'..."):
                file_bytes = uploaded_file.read()
                res = st.session_state.rag_engine.index_document(file_bytes, filename_tagged)
                if res["status"] == "indexed":
                    st.sidebar.success(f"Indexed {res['total_chunks']} chunks!")
                elif res["status"] == "skipped":
                    st.sidebar.info("Document already indexed.")
                else:
                    st.sidebar.error(res.get("reason", "Failed to index."))

# Get files indexed for this active notebook
all_chunks = st.session_state.rag_engine.vector_store.chunks
active_prefix = f"[NB-{active_notebook['id']}]"
notebook_files = sorted(list({
    c["metadata"]["filename"] for c in all_chunks if c["metadata"]["filename"].startswith(active_prefix)
}))

if notebook_files:
    st.sidebar.markdown("**Indexed Notebook Sources:**")
    for fname in notebook_files:
        clean_name = fname.replace(active_prefix, "").strip()
        c_name, c_del = st.sidebar.columns([0.8, 0.2])
        c_name.text(f"• {clean_name}")
        if c_del.button("❌", key=f"del_{fname}"):
            st.session_state.rag_engine.remove_document(fname)
            st.rerun()


# --- MAIN WORKSPACE TABS ---

tab_notes, tab_gen, tab_tutor, tab_analytics = st.tabs([
    "📝 Notebook & Saved Materials",
    "❓ Generate Questions & Exam",
    "📚 Grounded Smart Tutor",
    "📊 Notebook Analytics",
])


# =============================================================================
# TAB 1: NOTEBOOK & SAVED MATERIALS
# =============================================================================
with tab_notes:
    st.header(f"📓 Workspace: {active_notebook['title']}")
    if active_notebook["description"]:
        st.caption(active_notebook["description"])

    col_n1, col_n2 = st.columns([1, 1])

    with col_n1:
        st.subheader("➕ Create Manual Note / Reminder")
        with st.form("manual_note_form", clear_on_submit=True):
            note_title = st.text_input("Note Title", placeholder="e.g., Core Formula Reminders")
            note_content = st.text_area("Content / Key Takeaways", height=200, placeholder="Write formulas, definitions, or mistake notes here...")
            note_type = st.selectbox("Category", ["General", "Mistake Reminder"])
            if st.form_submit_button("Save Note to Notebook"):
                if note_title and note_content:
                    save_note(active_notebook["id"], note_title, note_content, note_type)
                    st.success("Note saved successfully!")
                    st.rerun()
                else:
                    st.warning("Please provide both title and content.")

    with col_n2:
        st.subheader("📁 Saved Notes & Materials in Notebook")
        saved_notes = get_notebook_notes(active_notebook["id"])
        if not saved_notes:
            st.info("No notes saved in this notebook yet. Generated questions and written notes will appear here.")
        else:
            for n in saved_notes:
                with st.expander(f"📌 [{n['note_type']}] {n['title']} ({n['created_at'][:10]})"):
                    st.markdown(n["content"])


# =============================================================================
# TAB 2: GENERATE QUESTIONS & EXAM (WITH CLEAR INSTRUCTIONS)
# =============================================================================
with tab_gen:
    st.header("❓ Question Generation & Exam Center")

    # CLEAR INSTRUCTION BOX ON HOW QUESTION GENERATION WORKS
    st.info(
        """
        **💡 How Question Generation Works:**
        1. **Select Sources:** Choose whether to generate questions using all sources uploaded to this notebook, a specific file, or general domain knowledge.
        2. **Configure Exam:** Select question format (MCQ or Written Essay), topic name, question count, and timer duration.
        3. **Generate & Save:** Click **Generate & Start Exam**. The generated questions will be used for your test **and automatically saved to this Notebook's Saved Materials**.
        """
    )

    col_cfg1, col_cfg2 = st.columns([1, 1])

    with col_cfg1:
        exam_format = st.radio("Select Question Format", ["Multiple Choice (MCQ)", "Written Essay"], horizontal=True)
        topic_name = st.text_input("Topic / Chapter Name", value="General Concepts")
        q_count = st.slider("Number of Questions to Generate", min_value=1, max_value=20, value=5)
        duration_mins = st.number_input("Exam Timer (Minutes)", min_value=1, max_value=120, value=10)

    with col_cfg2:
        source_options = ["All Sources in Active Notebook", "General Domain Knowledge (No Files)"] + [
            f.replace(active_prefix, "").strip() for f in notebook_files
        ]
        selected_source_option = st.selectbox("Select Context Source for Question Generation", options=source_options)

        # Context assembly logic
        context_text = None
        if selected_source_option == "All Sources in Active Notebook" and notebook_files:
            matching_chunks = [c["text"] for c in all_chunks if c["metadata"]["filename"].startswith(active_prefix)]
            context_text = "\n\n".join(matching_chunks[:15])
        elif selected_source_option not in ["All Sources in Active Notebook", "General Domain Knowledge (No Files)"]:
            raw_fname = f"{active_prefix} {selected_source_option}"
            matching_chunks = [c["text"] for c in all_chunks if c["metadata"]["filename"] == raw_fname]
            context_text = "\n\n".join(matching_chunks[:15])

    if st.button("🚀 Generate Questions & Start Exam", type="primary"):
        if not api_key:
            st.error("Please enter an OpenRouter API key in the sidebar.")
        else:
            with st.spinner("Generating grounded question paper..."):
                if exam_format == "Multiple Choice (MCQ)":
                    success, q_paper, model_used = generate_mcq_paper(
                        api_key=api_key,
                        subject=active_notebook["title"],
                        chapter=topic_name,
                        count=q_count,
                        context_document_text=context_text,
                        preferred_model=selected_model,
                    )
                else:
                    success, q_paper, model_used = generate_written_question_paper(
                        api_key=api_key,
                        subject=active_notebook["title"],
                        chapter=topic_name,
                        count=q_count,
                        context_document_text=context_text,
                        preferred_model=selected_model,
                    )

                if success and q_paper:
                    # Save generated questions into notebook notes automatically
                    formatted_saved_q = json.dumps(q_paper, indent=2)
                    save_note(
                        active_notebook["id"],
                        title=f"Generated {exam_format} Paper - {topic_name}",
                        content=f"```json\n{formatted_saved_q}\n```",
                        note_type="Generated Questions",
                    )

                    st.session_state.active_exam = {
                        "type": "MCQ" if exam_format == "Multiple Choice (MCQ)" else "WRITTEN",
                        "subject": active_notebook["title"],
                        "chapter": topic_name,
                        "questions": q_paper,
                        "model_used": model_used,
                    }
                    st.session_state.exam_timer = ExamTimer(duration_minutes=duration_mins)
                    st.session_state.exam_timer.start()
                    st.success("Questions generated and saved to notebook!")
                    st.rerun()
                else:
                    st.error("Failed to generate questions. Check API key or model availability.")

    # Active Exam Execution
    if st.session_state.active_exam:
        st.divider()
        exam = st.session_state.active_exam
        timer: ExamTimer = st.session_state.exam_timer
        
        st.warning(f"⏱️ Time Remaining: **{timer.get_formatted_status()['remaining_formatted']}**")
        st.subheader(f"Active Test: {exam['subject']} ({exam['type']})")

        with st.form("active_test_form"):
            user_responses = {}
            for idx, q in enumerate(exam["questions"]):
                st.markdown(f"**Q{idx + 1}: {q['question_text']}**")
                if exam["type"] == "MCQ":
                    user_responses[idx] = st.radio("Select Answer:", options=q["options"], key=f"q_mcq_{idx}", index=None)
                else:
                    user_responses[idx] = st.text_area("Your Answer:", key=f"q_writ_{idx}", height=120)
                st.divider()

            submit_test = st.form_submit_button("Submit Exam")

        if submit_test or timer.is_expired():
            st.subheader("📊 Exam Evaluation")
            if exam["type"] == "MCQ":
                results = score_mcq_submission(user_responses, exam["questions"])
                st.metric("Score", f"{results['score_percentage']}%", f"{results['correct_count']}/{results['total_questions']} Correct")

                for item in results["breakdown"]:
                    if item["is_correct"]:
                        st.success(f"**Q{item['question_index'] + 1}: Correct**\n\n{item['explanation']}")
                    else:
                        st.error(f"**Q{item['question_index'] + 1}: Incorrect**\n\nYour Answer: `{item['user_answer']}` | Correct: `{item['correct_answer']}`\n\n{item['explanation']}")
                        # Log mistake and save reminder note
                        log_id = log_mistake(
                            subject=exam["subject"],
                            chapter=exam["chapter"],
                            question_text=item["question_text"],
                            user_answer=item["user_answer"],
                            correct_answer=item["correct_answer"],
                            explanation=item["explanation"],
                            exam_type="MCQ",
                        )
                        save_note(
                            active_notebook["id"],
                            title=f"Mistake Reminder: {item['question_text'][:40]}...",
                            content=f"**Question:** {item['question_text']}\n\n**Your Wrong Answer:** {item['user_answer']}\n\n**Correct Answer:** {item['correct_answer']}\n\n**Explanation:** {item['explanation']}",
                            note_type="Mistake Reminder",
                        )
            else:
                for idx, q in enumerate(exam["questions"]):
                    ans = user_responses.get(idx, "")
                    eval_res = grade_written_exam(
                        api_key=api_key,
                        question=q["question_text"],
                        key_points=q["key_points"],
                        student_answer=ans,
                        preferred_model=selected_model,
                    )
                    st.markdown(f"**Q{idx + 1}: {q['question_text']}**")
                    st.metric("Score", f"{eval_res['total_score']} / 10 Points")
                    st.markdown(f"**Feedback:** {eval_res['detailed_feedback']}")

            st.session_state.active_exam = None
            st.session_state.exam_timer = None


# =============================================================================
# TAB 3: GROUNDED SMART TUTOR
# =============================================================================
with tab_tutor:
    st.header("📚 Smart Tutor & Document QA")
    st.caption(f"Ask questions grounded on sources inside notebook '{active_notebook['title']}'.")

    # Chat history display
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if query := st.chat_input(f"Ask about '{active_notebook['title']}' materials..."):
        if not api_key:
            st.error("API Key required.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": query})
            with st.chat_message("user"):
                st.markdown(query)

            with st.chat_message("assistant"):
                with st.spinner("Searching notebook sources..."):
                    success, resp, used_model, sources = st.session_state.rag_engine.ask_document(
                        api_key=api_key,
                        query=query,
                        preferred_model=selected_model,
                    )
                    if success and resp:
                        st.markdown(resp)
                        st.session_state.chat_history.append({"role": "assistant", "content": resp})
                    else:
                        st.error(resp or "Failed to generate tutor response.")


# =============================================================================
# TAB 4: NOTEBOOK ANALYTICS
# =============================================================================
with tab_analytics:
    st.header("📊 Notebook Analytics")
    summary = get_dashboard_summary()

    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.metric("Total Exams Taken", summary["total_exams_taken"])
    col_a2.metric("Overall Average Score", f"{summary['overall_average_score']}%")
    col_a3.metric("Study Streak", f"{summary['current_streak_days']} Days 🔥")
