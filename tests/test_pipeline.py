"""End-to-End Integration Smoke Test Suite for Gemini Study Studio."""

import os
import tempfile
import unittest
from unittest.mock import patch

from analytics import get_dashboard_summary
from database.database import init_db
from exam import score_mcq_submission
from mistakes import (
    calculate_sm2,
    get_due_mistakes,
    log_mistake,
    update_mistake_review,
)
from rag import RAGEngine


class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        # Create temporary SQLite DB and file storage directory for isolated testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_study.db")
        
        self.patcher = patch("config.DATABASE_PATH", self.db_path)
        self.mock_db_path = self.patcher.start()
        
        init_db(self.db_path)

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_sm2_algorithm(self):
        # Test perfect recall (q=5) progression
        interval, ef, reps, next_date = calculate_sm2(
            quality=5, previous_interval=1, previous_ef=2.5, repetitions=1
        )
        self.assertEqual(interval, 6)
        self.assertEqual(reps, 2)
        self.assertGreater(ef, 2.5)

        # Test failure (q=1) reset progression
        fail_interval, fail_ef, fail_reps, _ = calculate_sm2(
            quality=1, previous_interval=10, previous_ef=2.5, repetitions=4
        )
        self.assertEqual(fail_interval, 1)
        self.assertEqual(fail_reps, 0)

    def test_rag_ingestion_and_retrieval(self):
        rag = RAGEngine()
        sample_doc_bytes = b"Machine learning models require clean training datasets and validation curves."
        filename = "lecture_1.txt"

        # Test ingestion
        index_res = rag.index_document(sample_doc_bytes, filename)
        self.assertEqual(index_res["status"], "indexed")
        self.assertGreater(index_res["total_chunks"], 0)

        # Test vector retrieval
        retrieved = rag.retriever.retrieve(query="training dataset", top_k=2)
        self.assertGreater(len(retrieved), 0)
        self.assertEqual(retrieved[0]["metadata"]["filename"], filename)

    def test_mcq_scoring_and_mistake_flow(self):
        questions = [{
            "question_text": "What is 2 + 2?",
            "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
            "correct_answer": "B) 4",
            "explanation": "Basic addition.",
        }]

        # 1. Incorrect response submission
        user_answers = {0: "A) 3"}
        results = score_mcq_submission(user_answers, questions)
        self.assertEqual(results["correct_count"], 0)
        self.assertEqual(results["score_percentage"], 0.0)

        # 2. Log mistake
        wrong_item = results["breakdown"][0]
        log_id = log_mistake(
            subject="Math",
            chapter="Addition",
            question_text=wrong_item["question_text"],
            user_answer=wrong_item["user_answer"],
            correct_answer=wrong_item["correct_answer"],
            explanation=wrong_item["explanation"],
            exam_type="MCQ",
        )
        self.assertGreater(log_id, 0)

        # 3. Retrieve due mistakes
        due = get_due_mistakes(subject="Math")
        self.assertGreater(len(due), 0)

        # 4. Review mistake and update SM-2 schedule
        update_res = update_mistake_review(mistake_id=log_id, review_quality=4)
        self.assertEqual(update_res["new_interval_days"], 1)

    def test_analytics_summary(self):
        summary = get_dashboard_summary()
        self.assertIn("total_exams_taken", summary)
        self.assertIn("overall_average_score", summary)
        self.assertIn("current_streak_days", summary)


if __name__ == "__main__":
    unittest.main()"""End-to-End Integration Smoke Test Suite for Gemini Study Studio."""

import os
import tempfile
import unittest

from analytics import get_dashboard_summary
from database.database import init_db
from exam import score_mcq_submission
from mistakes import (
    calculate_sm2,
    get_due_mistakes,
    log_mistake,
    update_mistake_review,
)
from rag import RAGEngine


class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        # Create temporary SQLite DB and file storage directory for isolated testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_study.db")
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sm2_algorithm(self):
        # Test perfect recall (q=5) progression
        interval, ef, reps, next_date = calculate_sm2(
            quality=5, previous_interval=1, previous_ef=2.5, repetitions=1
        )
        self.assertEqual(interval, 6)
        self.assertEqual(reps, 2)
        self.assertGreater(ef, 2.5)

        # Test failure (q=1) reset progression
        fail_interval, fail_ef, fail_reps, _ = calculate_sm2(
            quality=1, previous_interval=10, previous_ef=2.5, repetitions=4
        )
        self.assertEqual(fail_interval, 1)
        self.assertEqual(fail_reps, 0)

    def test_rag_ingestion_and_retrieval(self):
        rag = RAGEngine()
        sample_doc_bytes = b"Machine learning models require clean training datasets and validation curves."
        filename = "lecture_1.txt"

        # Test ingestion
        index_res = rag.index_document(sample_doc_bytes, filename)
        self.assertEqual(index_res["status"], "indexed")
        self.assertGreater(index_res["total_chunks"], 0)

        # Test vector retrieval
        retrieved = rag.retriever.retrieve(query="training dataset", top_k=2)
        self.assertGreater(len(retrieved), 0)
        self.assertEqual(retrieved[0]["metadata"]["filename"], filename)

    def test_mcq_scoring_and_mistake_flow(self):
        questions = [{
            "question_text": "What is 2 + 2?",
            "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
            "correct_answer": "B) 4",
            "explanation": "Basic addition.",
        }]

        # 1. Incorrect response submission
        user_answers = {0: "A) 3"}
        results = score_mcq_submission(user_answers, questions)
        self.assertEqual(results["correct_count"], 0)
        self.assertEqual(results["score_percentage"], 0.0)

        # 2. Log mistake
        wrong_item = results["breakdown"][0]
        log_id = log_mistake(
            subject="Math",
            chapter="Addition",
            question_text=wrong_item["question_text"],
            user_answer=wrong_item["user_answer"],
            correct_answer=wrong_item["correct_answer"],
            explanation=wrong_item["explanation"],
            exam_type="MCQ",
        )
        self.assertGreater(log_id, 0)

        # 3. Retrieve due mistakes
        due = get_due_mistakes(subject="Math")
        self.assertGreater(len(due), 0)

        # 4. Review mistake and update SM-2 schedule
        update_res = update_mistake_review(mistake_id=log_id, review_quality=4)
        self.assertEqual(update_res["new_interval_days"], 1)

    def test_analytics_summary(self):
        summary = get_dashboard_summary()
        self.assertIn("total_exams_taken", summary)
        self.assertIn("overall_average_score", summary)
        self.assertIn("current_streak_days", summary)


if __name__ == "__main__":
    unittest.main()
