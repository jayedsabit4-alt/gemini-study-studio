"""Gemini Study Studio - Streamlit Application Entrypoint."""

import os
from typing import Dict, List
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Gemini Study Studio",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

from analytics import get_dashboard_summary
from config import DEFAULT_MODEL, FALLBACK_MODELS, UPLOAD_FOLDER
from database.database import get_db_connection, init_db
from exam import (
    ExamTimer,
    generate_mcq_paper,
    generate_written_question_paper,
    grade_written_exam,
    score_mcq_submission,
)
from llm.llm_client import generate_response
from mistakes import (
    generate_adaptive_revision_notes,
    get_due_mistakes,
    log_mistake,
    update_mistake_review,
)
from rag import RAGEngine
from ui.styles import apply_custom_styles

# Initialize Database Schema
init_db()

# Apply UI CSS Styling
apply_custom_styles()


# Initialize Session State
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "active_exam" not in st.session_state:
    st.session_state.active_exam = None

if "exam_timer" not in st.session_state:
    st.session_state.exam_timer = None


def save_exam_record(
    subject: str,
    chapter: str,
    exam_type: str,
    total_questions: int,
    score_percentage: float,
    model_used: str,
):
    """Persists completed exam score and logs study session for streak tracking."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO exam_results (
                subject, chapter, exam_type, total_questions, score_percentage, model_used
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (subject, chapter, exam_type, total_questions, score_percentage, model_used),
        )
        cursor.execute(
            """
            INSERT INTO study_sessions (session_type, duration_seconds)
            VALUES (?, ?)
            """,
            (f"EXAM_{exam_type}", 0),
        )
        conn.commit()
    finally:
        conn.close()


def log_activity_session(session_type: str):
    """Logs active daily study session to maintain study streak analytics."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO study_sessions (session_type, duration_seconds)
            VALUES (?, ?)
            """,
            (session_type, 0),
        )
        conn.commit()
    finally:
        conn.close()


# --- SIDEBAR CONFIGURATION ---

st.sidebar.title("🎓 Study Studio")
st.sidebar.caption("AI Academic Preparation & RAG Engine")

# 1. API Key Input
api_key = st.sidebar.text_input(
    "OpenRouter API Key",
    type="password",
    help="Enter your OpenRouter API key to enable LLM operations.",
    value=os.getenv("OPENROUTER_API_KEY", ""),
)

# 2. Model Selection
selected_model = st.sidebar.selectbox(
    "LLM Model Target",
    options=FALLBACK_MODELS,
    index=0,
)

st.sidebar.divider()

# 3. RAG Document Ingestion Management
st.sidebar.subheader("📄 Material Library")
uploaded_files = st.sidebar.file_uploader(
    "Upload Study Documents",
    type=["pdf", "docx", "pptx", "txt", "md", "csv", "xlsx", "png", "jpg", "jpeg", "json"],
    accept_multiple_files=True,
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        if st.sidebar.button(f"Index {uploaded_file.name}", key=f"btn_{uploaded_file.name}"):
            with st.spinner(f"Indexing '{uploaded_file.name}'..."):
                file_bytes = uploaded_file.read()
                res = st.session_state.rag_engine.index_document(file_bytes, uploaded_file.name)
                
                if res["status"] == "indexed":
                    st.sidebar.success(f"Indexed {res['total_chunks']} chunks from {uploaded_file.name}")
                elif res["status"] == "skipped":
                    st.sidebar.info(res["message"])
                else:
                    st.sidebar.error(res.get("reason", "Failed to index document."))

# Display Indexed Files List
indexed_chunks = st.session_state.rag_engine.vector_store.chunks
indexed_files = sorted(list({c["metadata"]["filename"] for c in indexed_chunks}))

if indexed_files:
    st.sidebar.markdown("**Indexed Files:**")
    for fname in indexed_files:
        col_name, col_del = st.sidebar.columns([0.8, 0.2])
        col_name.text(f"• {fname}")
        if col_del.button("❌", key=f"del_{fname}"):
            st.session_state.rag_engine.remove_document(fname)
            st.rerun()


# --- MAIN INTERFACE TABS ---

tab_chat, tab_exam, tab_spaced, tab_analytics = st.tabs([
    "📚 Smart Tutor & RAG",
    "📝 Exam Center",
    "🔁 Spaced Repetition",
    "📊 Performance Analytics",
])


# =============================================================================
# TAB 1: SMART TUTOR & RAG QA
# =============================================================================
with tab_chat:
    st.header("Smart Study & Document QA")
    st.caption("Ask questions grounded strictly on your uploaded materials or converse with the general tutor.")

    use_rag = st.checkbox("Ground response in indexed document library", value=True if indexed_files else False)
    
    selected_doc_filter = None
    if use_rag and indexed_files:
        selected_doc_filter = st.selectbox(
            "Filter Source Document",
            options=["All Indexed Documents"] + indexed_files,
        )
        if selected_doc_filter == "All Indexed Documents":
            selected_doc_filter = None

    # Render Active Conversation
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander("🔍 View Context Sources"):
                    for src in msg["sources"]:
                        st.markdown(f"**Source:** `{src['metadata']['filename']}` (Page {src['metadata'].get('page_number', 1)})")
                        st.caption(src["text"])

    # User Input Field
    if user_query := st.chat_input("Ask a concept question or request a summary..."):
        if not api_key:
            st.error("Please enter an OpenRouter API Key in the sidebar to generate responses.")
        else:
            log_activity_session("SMART_TUTOR_CHAT")
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing study context & generating response..."):
                    if use_rag:
                        success, resp_text, used_model, sources = st.session_state.rag_engine.ask_document(
                            api_key=api_key,
                            query=user_query,
                            preferred_model=selected_model,
                            filename_filter=selected_doc_filter,
                        )
                    else:
                        messages = [{"role": "system", "content": "You are an expert academic tutor."}]
                        messages.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history])
                        success, resp_text, used_model = generate_response(
                            api_key=api_key,
                            messages=messages,
                            preferred_model=selected_model,
                        )
                        sources = []

                    if success and resp_text:
                        st.markdown(resp_text)
                        st.caption(f"Generated via `{used_model}`")
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": resp_text,
                            "sources": sources,
                        })
                    else:
                        st.error(resp_text or "Failed to generate AI response.")


# =============================================================================
# TAB 2: EXAM CENTER (MCQS & WRITTEN)
# =============================================================================
with tab_exam:
    st.header("Exam Center")
    st.caption("Generate grounded mock exams, take timed tests, and receive instant rubric feedback.")

    exam_mode = st.radio("Select Exam Format", ["Multiple Choice (MCQ)", "Written Essay"], horizontal=True)

    col_setup, col_ground = st.columns([1, 1])
    with col_setup:
        subject_input = st.text_input("Subject Name", value="Statistics")
        chapter_input = st.text_input("Chapter / Topic", value="Probability Distributions")
        question_count = st.slider("Question Count", min_value=1, max_value=20, value=5)
        duration_mins = st.number_input("Exam Duration (Minutes)", min_value=1, max_value=120, value=10)

    with col_ground:
        ground_doc = st.selectbox(
            "Ground Exam on Uploaded File (Optional)",
            options=["None (General Domain Knowledge)"] + indexed_files,
        )
        context_text = None
        if ground_doc != "None (General Domain Knowledge)":
            matching_chunks = [
                c["text"] for c in st.session_state.rag_engine.vector_store.chunks
                if c["metadata"].get("filename") == ground_doc
            ]
            context_text = "\n\n".join(matching_chunks[:10])

    if st.button("🚀 Generate & Start Exam", type="primary"):
        if not api_key:
            st.error("API Key required.")
        else:
            with st.spinner("Generating exam paper..."):
                if exam_mode == "Multiple Choice (MCQ)":
                    success, q_paper, model_used = generate_mcq_paper(
                        api_key=api_key,
                        subject=subject_input,
                        chapter=chapter_input,
                        count=question_count,
                        context_document_text=context_text,
                        preferred_model=selected_model,
                    )
                else:
                    success, q_paper, model_used = generate_written_question_paper(
                        api_key=api_key,
                        subject=subject_input,
                        chapter=chapter_input,
                        count=question_count,
                        context_document_text=context_text,
                        preferred_model=selected_model,
                    )

                if success and q_paper:
                    st.session_state.active_exam = {
                        "type": "MCQ" if exam_mode == "Multiple Choice (MCQ)" else "WRITTEN",
                        "subject": subject_input,
                        "chapter": chapter_input,
                        "questions": q_paper,
                        "answers": {},
                        "model_used": model_used,
                    }
                    st.session_state.exam_timer = ExamTimer(duration_minutes=duration_mins)
                    st.session_state.exam_timer.start()
                    st.success("Exam paper generated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to generate exam paper. Check model status.")

    # Render Active Test Session
    if st.session_state.active_exam:
        st.divider()
        exam = st.session_state.active_exam
        timer: ExamTimer = st.session_state.exam_timer
        
        timer_status = timer.get_formatted_status()
        st.warning(f"⏱️ Time Remaining: **{timer_status['remaining_formatted']}**")

        st.subheader(f"Active Exam: {exam['subject']} ({exam['type']})")

        with st.form("exam_form"):
            user_responses = {}
            for idx, q in enumerate(exam["questions"]):
                st.markdown(f"**Q{idx + 1}: {q['question_text']}**")
                
                if exam["type"] == "MCQ":
                    user_responses[idx] = st.radio(
                        "Select Answer:",
                        options=q["options"],
                        key=f"mcq_{idx}",
                        index=None,
                    )
                else:
                    user_responses[idx] = st.text_area(
                        "Your Written Response:",
                        key=f"written_{idx}",
                        height=150,
                    )
                st.divider()

            submit_exam = st.form_submit_button("Submit Exam For Grading")

        if submit_exam or timer.is_expired():
            st.subheader("📊 Exam Evaluation Results")

            if exam["type"] == "MCQ":
                results = score_mcq_submission(user_responses, exam["questions"])
                st.metric("Final Score", f"{results['score_percentage']}%", f"{results['correct_count']}/{results['total_questions']} Correct")

                save_exam_record(
                    subject=exam["subject"],
                    chapter=exam["chapter"],
                    exam_type="MCQ",
                    total_questions=results["total_questions"],
                    score_percentage=results["score_percentage"],
                    model_used=exam.get("model_used", selected_model),
                )

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
            else:
                total_points = 0
                max_possible_points = len(exam["questions"]) * 10

                for idx, q in enumerate(exam["questions"]):
                    ans = user_responses.get(idx, "")
                    eval_res = grade_written_exam(
                        api_key=api_key,
                        question=q["question_text"],
                        key_points=q["key_points"],
                        student_answer=ans,
                        preferred_model=selected_model,
                    )
                    earned = eval_res["total_score"]
                    total_points += earned

                    st.markdown(f"**Q{idx + 1}: {q['question_text']}**")
                    st.metric("Graded Score", f"{earned} / 10 Points")
                    st.markdown(f"**Feedback:** {eval_res['detailed_feedback']}")

                written_pct = round((total_points / max_possible_points * 100), 2) if max_possible_points > 0 else 0.0
                save_exam_record(
                    subject=exam["subject"],
                    chapter=exam["chapter"],
                    exam_type="WRITTEN",
                    total_questions=len(exam["questions"]),
                    score_percentage=written_pct,
                    model_used=exam.get("model_used", selected_model),
                )

            # Reset Active Exam and Timer State
            st.session_state.active_exam = None
            st.session_state.exam_timer = None


# =============================================================================
# TAB 3: SPACED REPETITION (SM-2 REVISION)
# =============================================================================
with tab_spaced:
    st.header("Spaced Repetition Flashcards (SM-2)")
    st.caption("Review mistaken concepts scheduled for revision today based on recall difficulty.")

    due_mistakes = get_due_mistakes()

    col_m_actions, col_m_rev = st.columns([0.7, 0.3])
    with col_m_rev:
        if st.button("✨ Generate AI Revision Guide from Mistakes"):
            if not api_key:
                st.error("API Key required.")
            elif not due_mistakes:
                st.info("No active mistakes logged to generate revision guide.")
            else:
                with st.spinner("Generating AI revision guide..."):
                    mistakes_summary_str = "\n".join([
                        f"- Subject: {m['subject']}, Q: {m['question_text']}, Wrong: {m['user_answer']}, Correct: {m['correct_answer']}"
                        for m in due_mistakes
                    ])
                    success, rev_notes, model_used = generate_adaptive_revision_notes(
                        api_key=api_key,
                        mistakes_data=mistakes_summary_str,
                        preferred_model=selected_model,
                    )
                    if success:
                        st.markdown(rev_notes)
                    else:
                        st.error("Failed to generate revision guide.")

    if not due_mistakes:
        st.balloons()
        st.success("🎉 You are all caught up! No mistakes due for review right now.")
    else:
        st.info(f"You have **{len(due_mistakes)}** mistake logs scheduled for revision.")
        
        current_item = due_mistakes[0]
        st.subheader(f"Subject: {current_item['subject']} | Chapter: {current_item['chapter']}")

        with st.container():
            st.markdown(f"### Question:\n{current_item['question_text']}")
            
            with st.expander("👁️ Reveal Correct Answer & Explanation"):
                st.markdown(f"**Your Previous Answer:** `{current_item['user_answer']}`")
                st.markdown(f"**Correct Answer:** `{current_item['correct_answer']}`")
                st.markdown(f"**Explanation:** {current_item['explanation']}")

            st.divider()
            st.markdown("**Rate Your Recall Quality (SM-2):**")
            
            col_q0, col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(6)
            
            ratings = [
                (col_q0, "0: Blackout", 0),
                (col_q1, "1: Wrong", 1),
                (col_q2, "2: Hard", 2),
                (col_q3, "3: Pass", 3),
                (col_q4, "4: Good", 4),
                (col_q5, "5: Perfect", 5),
            ]

            for col, label, q_val in ratings:
                if col.button(label, key=f"rate_{q_val}"):
                    update_res = update_mistake_review(current_item["id"], review_quality=q_val)
                    log_activity_session("SPACED_REPETITION_REVIEW")
                    st.success(f"Updated! Next review in {update_res['new_interval_days']} days.")
                    st.rerun()


# =============================================================================
# TAB 4: PERFORMANCE ANALYTICS
# =============================================================================
with tab_analytics:
    st.header("Analytics & Mastery Tracker")
    st.caption("Monitor exam history, study streaks, and subject proficiency tiers.")

    summary = get_dashboard_summary()

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Exams Taken", summary["total_exams_taken"])
    col_m2.metric("Overall Average Score", f"{summary['overall_average_score']}%")
    col_m3.metric("Daily Study Streak", f"{summary['current_streak_days']} Days 🔥")
    col_m4.metric("Mistakes Due for Review", summary["due_mistakes_count"])

    st.divider()
    st.subheader("Subject Proficiency Tiers")

    mastery_data = summary["mastery_by_subject"]
    if not mastery_data:
        st.info("No exam data recorded yet. Complete mock tests to view subject mastery breakdowns.")
    else:
        df_mastery = pd.DataFrame(mastery_data)
        st.dataframe(
            df_mastery,
            column_config={
                "subject": "Subject Name",
                "total_exams": "Exams Taken",
                "average_score": st.column_config.NumberColumn("Average Score (%)", format="%.2f%%"),
                "highest_score": st.column_config.NumberColumn("Highest Score (%)", format="%.2f%%"),
                "mastery_tier": "Mastery Level",
            },
            hide_index=True,
            use_container_width=True,
        )
