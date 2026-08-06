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

# Initialize Database & Styles
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


# --- SIDEBAR WORKSPACE ---

st.sidebar.title("📓 Notebook Manager")

api_key = st.sidebar.text_input(
    "OpenRouter API Key",
    type="password",
    value=os.getenv("OPENROUTER_API_KEY", ""),
    help="Required for LLM operations.",
)

selected_model = st.sidebar.selectbox("LLM Model Target", options=FALLBACK_MODELS, index=0)

st.sidebar.divider()

st.sidebar.subheader("➕ Create Notebook")
with st.sidebar.form("create_notebook_form", clear_on_submit=True):
    new_nb_title = st.text_input("Notebook Title", placeholder="e.g., Statistics Workspace")
    new_nb_desc = st.text_area("Description", placeholder="Optional description...")
    if st.form_submit_button("Create Workspace"):
        if new_nb_title.strip():
            create_notebook(new_nb_title, new_nb_desc)
            st.sidebar.success("Notebook created!")
            st.rerun()

all_notebooks = get_all_notebooks()
if not all_notebooks:
    st.sidebar.info("Create a notebook above to begin.")
    st.warning("⚠️ Please create a Notebook from the sidebar first.")
    st.stop()

nb_options = {f"{nb['title']}": nb for nb in all_notebooks}
selected_nb_label = st.sidebar.selectbox("Active Workspace", options=list(nb_options.keys()))
active_notebook = nb_options[selected_nb_label]

if st.sidebar.button("🗑️ Delete Current Notebook"):
    delete_notebook(active_notebook["id"])
    st.rerun()

st.sidebar.divider()

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
                    st.sidebar.info("Already indexed.")
                else:
                    st.sidebar.error(res.get("reason", "Failed to index."))

all_chunks = st.session_state.rag_engine.vector_store.chunks
active_prefix = f"[NB-{active_notebook['id']}]"
notebook_files = sorted(list({
    c["metadata"]["filename"] for c in all_chunks if c["metadata"]["filename"].startswith(active_prefix)
}))

if notebook_files:
    st.sidebar.markdown("**Indexed Files:**")
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
    "❓ Question Generator & Exam",
    "📚 Smart Tutor",
    "📊 Analytics",
])


# =============================================================================
# TAB 1: NOTEBOOK & SAVED MATERIALS
# =============================================================================
with tab_notes:
    st.header(f"📓 Workspace: {active_notebook['title']}")
    col_n1, col_n2 = st.columns([1, 1])

    with col_n1:
        st.subheader("➕ Add Manual Note")
        with st.form("manual_note_form", clear_on_submit=True):
            note_title = st.text_input("Title")
            note_content = st.text_area("Content", height=180)
            note_type = st.selectbox("Category", ["General", "Mistake Reminder"])
            if st.form_submit_button("Save Note"):
                if note_title and note_content:
                    save_note(active_notebook["id"], note_title, note_content, note_type)
                    st.success("Saved!")
                    st.rerun()

    with col_n2:
        st.subheader("📁 Saved Notebook Materials")
        saved_notes = get_notebook_notes(active_notebook["id"])
        if not saved_notes:
            st.info("No saved notes yet. Generated questions and mistake notes will appear here.")
        else:
            for n in saved_notes:
                with st.expander(f"📌 [{n['note_type']}] {n['title']}"):
                    st.markdown(n["content"])


# =============================================================================
# TAB 2: QUESTION GENERATOR & EXAM CENTER
# =============================================================================
with tab_gen:
    st.header("❓ Question Generator & Timed Exam Center")

    exam_format = st.radio("Select Format", ["Multiple Choice (MCQ)", "Written Essay"], horizontal=True)

    # DYNAMIC INSTRUCTION BOX BASED ON EXAM FORMAT
    if exam_format == "Multiple Choice (MCQ)":
        st.info(
            """
            **💡 Instructions for Multiple Choice (MCQ) Mode:**
            1. **Select Source:** Ground your questions on uploaded files or general domain knowledge.
            2. **Set Question Count:** Enter any custom number of questions (up to 100).
            3. **Generate & Save:** Questions are created via LLM and saved automatically to your **Notebook Materials**.
            4. **Instant Scoring & Review:** Submit your test to view instant breakdown and log wrong answers into spaced repetition.
            """
        )
    else:
        st.info(
            """
            **💡 Instructions for Written Essay Mode:**
            1. **Select Source:** Questions will be grounded on your uploaded notebook materials.
            2. **Set Question Count:** Specify how many written essay prompts you want (up to 100).
            3. **Type Responses:** Write your answers in the input boxes before the session timer expires.
            4. **Rubric Evaluation:** AI evaluates your answers out of 10 points across Content, Logic, Terminology, and Grammar.
            """
        )

    col_cfg1, col_cfg2 = st.columns([1, 1])

    with col_cfg1:
        topic_name = st.text_input("Chapter / Topic Name", value="Core Concepts")
        
        # FLEXIBLE NUMBER INPUT: UNLOCKED UP TO 100 QUESTIONS
        q_count = st.number_input("Number of Questions to Generate", min_value=1, max_value=100, value=5, step=1)
        duration_mins = st.number_input("Exam Timer (Minutes)", min_value=1, max_value=180, value=15)

    with col_cfg2:
        source_options = ["All Notebook Sources", "General Domain Knowledge"] + [
            f.replace(active_prefix, "").strip() for f in notebook_files
        ]
        selected_source_option = st.selectbox("Grounding Source Context", options=source_options)

        context_text = None
        if selected_source_option == "All Notebook Sources" and notebook_files:
            matching_chunks = [c["text"] for c in all_chunks if c["metadata"]["filename"].startswith(active_prefix)]
            context_text = "\n\n".join(matching_chunks[:15])
        elif selected_source_option not in ["All Notebook Sources", "General Domain Knowledge"]:
            raw_fname = f"{active_prefix} {selected_source_option}"
            matching_chunks = [c["text"] for c in all_chunks if c["metadata"]["filename"] == raw_fname]
            context_text = "\n\n".join(matching_chunks[:15])

    if st.button("🚀 Generate Questions & Start Test", type="primary"):
        if not api_key:
            st.error("Please enter an OpenRouter API key in the sidebar.")
        else:
            with st.spinner(f"Generating {q_count} questions via AI..."):
                if exam_format == "Multiple Choice (MCQ)":
                    success, q_paper, model_used = generate_mcq_paper(
                        api_key=api_key,
                        subject=active_notebook["title"],
                        chapter=topic_name,
                        count=int(q_count),
                        context_document_text=context_text,
                        preferred_model=selected_model,
                    )
                else:
                    success, q_paper, model_used = generate_written_question_paper(
                        api_key=api_key,
                        subject=active_notebook["title"],
                        chapter=topic_name,
                        count=int(q_count),
                        context_document_text=context_text,
                        preferred_model=selected_model,
                    )

                if success and q_paper:
                    # Auto-save questions to notebook
                    formatted_q = json.dumps(q_paper, indent=2)
                    save_note(
                        active_notebook["id"],
                        title=f"Generated {exam_format} - {topic_name}",
                        content=f"```json\n{formatted_q}\n```",
                        note_type="Generated Questions",
                    )

                    st.session_state.active_exam = {
                        "type": "MCQ" if exam_format == "Multiple Choice (MCQ)" else "WRITTEN",
                        "subject": active_notebook["title"],
                        "chapter": topic_name,
                        "questions": q_paper,
                        "model_used": model_used,
                    }
                    st.session_state.exam_timer = ExamTimer(duration_minutes=int(duration_mins))
                    st.session_state.exam_timer.start()
                    st.success("Questions generated and saved to notebook!")
                    st.rerun()
                else:
                    st.error("Question generation failed. Check API key or target model.")

    # Active Test Evaluation
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
            st.subheader("📊 Exam Evaluation Results")
            if exam["type"] == "MCQ":
                results = score_mcq_submission(user_responses, exam["questions"])
                st.metric("Score", f"{results['score_percentage']}%", f"{results['correct_count']}/{results['total_questions']} Correct")

                for item in results["breakdown"]:
                    if item["is_correct"]:
                        st.success(f"**Q{item['question_index'] + 1}: Correct**\n\n{item['explanation']}")
                    else:
                        st.error(f"**Q{item['question_index'] + 1}: Incorrect**\n\nYour Answer: `{item['user_answer']}` | Correct: `{item['correct_answer']}`\n\n{item['explanation']}")
                        log_mistake(
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
                            title=f"Mistake Reminder: {item['question_text'][:35]}...",
                            content=f"**Question:** {item['question_text']}\n\n**Your Answer:** {item['user_answer']}\n\n**Correct Answer:** {item['correct_answer']}\n\n**Explanation:** {item['explanation']}",
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
# TAB 3: SMART TUTOR
# =============================================================================
with tab_tutor:
    st.header("📚 Smart Tutor & RAG QA")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if query := st.chat_input("Ask about your notebook materials..."):
        if not api_key:
            st.error("API Key required.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": query})
            with st.chat_message("user"):
                st.markdown(query)

            with st.chat_message("assistant"):
                with st.spinner("Searching sources..."):
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
# TAB 4: ANALYTICS
# =============================================================================
with tab_analytics:
    st.header("📊 Notebook Analytics")
    summary = get_dashboard_summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Exams Taken", summary["total_exams_taken"])
    c2.metric("Average Score", f"{summary['overall_average_score']}%")
    c3.metric("Study Streak", f"{summary['current_streak_days']} Days 🔥")
