"""
storage.py — Persistent storage for Coffee Chat Bot.
Handles pairing history and active channel tracking via a local JSON file.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

STORAGE_FILE = "coffee_chat_storage.json"


class Storage:
    def __init__(self, filepath: str = STORAGE_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                return json.load(f)
        logger.info(f"No storage file found at {self.filepath}. Starting fresh.")
        return {
            "pairs_history": {},   # "YYYY-MM" -> [[user1, user2], ...]
            "active_channels": {}  # channel_id -> {members, created_at, reminded, archived}
        }

    def save(self):
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2)
        logger.debug(f"Storage saved to {self.filepath}")

    # ── Pairing History ────────────────────────────────────────────────────────

    def already_paired_this_month(self, month_key: str) -> bool:
        return month_key in self.data["pairs_history"]

    def add_month_pairs(self, month_key: str, pairs: List[List[str]]):
        self.data["pairs_history"][month_key] = [list(p) for p in pairs]
        self.save()
        logger.info(f"Saved {len(pairs)} pairs for {month_key}")

    def get_historical_pairs(self) -> Set[frozenset]:
        """Return all historical pairs as frozensets for O(1) lookup."""
        all_pairs: Set[frozenset] = set()
        for month_pairs in self.data["pairs_history"].values():
            for pair in month_pairs:
                # For trios, record every combination as a "seen" pair
                for i in range(len(pair)):
                    for j in range(i + 1, len(pair)):
                        all_pairs.add(frozenset([pair[i], pair[j]]))
        return all_pairs

    # ── Active Channels ────────────────────────────────────────────────────────

    def add_active_channel(self, channel_id: str, members: List[str]):
        self.data["active_channels"][channel_id] = {
            "members": members,
            "created_at": datetime.now().isoformat(),
            "reminded": False,
            "archived": False,
        }
        self.save()

    def get_active_channels(self) -> Dict[str, dict]:
        return {
            cid: info
            for cid, info in self.data["active_channels"].items()
            if not info.get("archived", False)
        }

    def mark_reminded(self, channel_id: str):
        if channel_id in self.data["active_channels"]:
            self.data["active_channels"][channel_id]["reminded"] = True
            self.save()

    def mark_archived(self, channel_id: str):
        if channel_id in self.data["active_channels"]:
            self.data["active_channels"][channel_id]["archived"] = True
            self.save()
