import os
import json
import logging
from typing import Set, Dict, List
from config import DRAFTED_JOBS_FILE

logger = logging.getLogger("draft_manager")

class DraftManager:
    def __init__(self, storage_file: str = DRAFTED_JOBS_FILE):
        self.storage_file = os.path.abspath(storage_file)
        self.drafted_records: Dict[str, Dict] = self._load()

    def _load(self) -> Dict[str, Dict]:
        """Load records of previously drafted job applications."""
        if not os.path.exists(self.storage_file):
            return {}
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Support both list of IDs and dictionary of records
                if isinstance(data, list):
                    return {str(jid): {"job_id": str(jid)} for jid in data}
                return {str(k): v for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Could not load drafted jobs from {self.storage_file}: {e}")
            return {}

    def _save(self):
        """Persist drafted records to disk."""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.drafted_records, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save drafted jobs to {self.storage_file}: {e}")

    def is_drafted(self, job_id: str) -> bool:
        """Check if a draft was already generated for this job ID."""
        if not job_id:
            return True
        clean_id = str(job_id).split(".")[0].strip()
        return clean_id in self.drafted_records

    def mark_drafted(self, job_id: str, record: Dict = None):
        """Record that a draft has been created for a given job."""
        if not job_id:
            return
        clean_id = str(job_id).split(".")[0].strip()
        self.drafted_records[clean_id] = record or {"job_id": clean_id}
        self._save()

    def get_all_drafted_ids(self) -> Set[str]:
        return set(self.drafted_records.keys())

    def get_total_drafted(self) -> int:
        return len(self.drafted_records)
