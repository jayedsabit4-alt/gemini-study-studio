"""Exam Session Timer and Duration Tracking Utilities."""

from datetime import datetime, timedelta
from typing import Dict, Optional, Union


class ExamTimer:
    """Tracks time remaining and elapsed seconds for timed exam sessions."""

    def __init__(self, duration_minutes: int):
        self.duration_seconds = duration_minutes * 60
        self.start_time: Optional[datetime] = None

    def start(self):
        """Starts timing session."""
        self.start_time = datetime.now()

    def get_elapsed_seconds(self) -> int:
        """Returns total elapsed seconds since session start."""
        if self.start_time is None:
            return 0
        delta = datetime.now() - self.start_time
        return int(delta.total_seconds())

    def get_remaining_seconds(self) -> int:
        """Returns remaining seconds before time expires."""
        elapsed = self.get_elapsed_seconds()
        remaining = self.duration_seconds - elapsed
        return max(0, remaining)

    def is_expired(self) -> bool:
        """Checks if timer duration has run out."""
        return self.get_remaining_seconds() == 0

    def get_formatted_status(self) -> Dict[str, Union[str, bool]]:
        """Returns formatted representation dictionary for UI countdowns."""
        remaining = self.get_remaining_seconds()
        elapsed = self.get_elapsed_seconds()

        rem_td = timedelta(seconds=remaining)
        el_td = timedelta(seconds=elapsed)

        return {
            "remaining_formatted": str(rem_td).split(".")[0],
            "elapsed_formatted": str(el_td).split(".")[0],
            "is_expired": self.is_expired(),
        }
