import json
import os
from pathlib import Path
from typing import List

from bot.analytics.match_record import MatchRecord

# bot root folder (next to run.py), independent of the current working directory
DATA_DIR: Path = Path(__file__).resolve().parents[2] / "data"


class MatchHistory:
    """
    Persists finished matches in a JSON Lines file (one match per line, append only),
    and the match being played in a separate file so it can be recovered after a crash.
    """
    matches_file: Path
    current_file: Path

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.matches_file = data_dir / "matches.jsonl"
        self.current_file = data_dir / "current_match.json"

    def load(self) -> List[MatchRecord]:
        if (not self.matches_file.is_file()):
            return []
        records: List[MatchRecord] = []
        with open(self.matches_file, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if (not line):
                    continue
                try:
                    records.append(MatchRecord.from_dict(json.loads(line)))
                except Exception as e:
                    # a corrupted line must never block the rest of the history
                    print(f"[MatchHistory] Skipping invalid line {line_number}: {e}")
        return records

    def append(self, record: MatchRecord) -> None:
        self.matches_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.matches_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict()) + "\n")

    def save_current(self, record: MatchRecord) -> None:
        self.current_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file: Path = self.current_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as handle:
            json.dump(record.to_dict(), handle)
        os.replace(temp_file, self.current_file)

    def pop_current(self) -> MatchRecord | None:
        if (not self.current_file.is_file()):
            return None
        try:
            with open(self.current_file, "r", encoding="utf-8") as handle:
                return MatchRecord.from_dict(json.load(handle))
        except Exception as e:
            print(f"[MatchHistory] Invalid current match file: {e}")
            return None
        finally:
            self.current_file.unlink(missing_ok=True)
