import os
import json
import logging
from typing import Set
from config import HISTORY_FILE_PATH

logger = logging.getLogger("history_tracker")

class HistoryTracker:
    def __init__(self, history_file: str = HISTORY_FILE_PATH):
        self.history_file = os.path.abspath(history_file)
        self.seen_ids: Set[str] = self._load_history()

    def _load_history(self) -> Set[str]:
        """Load set of previously processed Job IDs from JSON file."""
        if not os.path.exists(self.history_file):
            logger.info("No existing history file found. Initializing empty history.")
            return set()

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                seen = set(str(jid).strip() for jid in data if str(jid).strip())
                logger.info(f"Loaded {len(seen)} previously processed Job ID(s) from history.")
                return seen
        except Exception as e:
            logger.warning(f"Failed to load job history from {self.history_file}: {e}")
            return set()

    def is_seen(self, job_id: str) -> bool:
        """Check if job_id was already processed in a previous run."""
        if not job_id:
            return True
        clean_id = str(job_id).split(".")[0].strip()
        return clean_id in self.seen_ids

    def mark_seen(self, job_ids: list):
        """Add new job IDs to history set and persist to disk."""
        new_added = 0
        for jid in job_ids:
            if jid:
                clean_id = str(jid).split(".")[0].strip()
                if clean_id and clean_id not in self.seen_ids:
                    self.seen_ids.add(clean_id)
                    new_added += 1

        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(list(self.seen_ids), f, indent=2)
            logger.info(f"Updated history file with {new_added} new Job ID(s). Total tracked: {len(self.seen_ids)}.")
        except Exception as e:
            logger.error(f"Failed to save job history to {self.history_file}: {e}")
