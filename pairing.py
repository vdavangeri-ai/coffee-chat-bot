"""
pairing.py — Smart pairing engine for Coffee Chat Bot.

Rules (applied strictly first, then relaxed if needed):
  1. No repeat pairs from previous months
  2. Cross designation (analyst ≠ analyst)
  3. Cross office (different location)

When an odd number of members exists, one group of 3 is created.
"""

import random
import logging
from typing import Dict, List, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class PairingEngine:
    """
    Builds optimal coffee-chat pairs from a member list, a roster DataFrame,
    and a set of historical pairs to avoid repeats.
    """

    # Scoring constants
    SCORE_CROSS_DESIGNATION = 3.0
    SCORE_CROSS_OFFICE = 3.0
    SCORE_SAME_DESIGNATION_PENALTY = -5.0  # applied in strict mode
    SCORE_SAME_OFFICE_PENALTY = -5.0       # applied in strict mode
    SCORE_REPEAT_PAIR_PENALTY = -100.0

    def __init__(self, roster: pd.DataFrame, historical_pairs: Set[frozenset]):
        """
        Args:
            roster: DataFrame with columns [slack_user_id, designation, office]
            historical_pairs: frozensets of previously paired user IDs
        """
        self.roster = roster.set_index("slack_user_id")
        self.historical_pairs = historical_pairs

    # ── Public API ─────────────────────────────────────────────────────────────

    def create_pairs(self, members: List[str]) -> List[List[str]]:
        """
        Create the best possible pairs/trios from the member list.
        Tries strict rules first, then relaxes constraints, then falls back
        to random pairing.
        """
        if len(members) < 2:
            logger.warning("Fewer than 2 eligible members — nothing to pair.")
            return []

        members = list(members)

        for strict in (True, False):
            mode = "strict" if strict else "relaxed"
            logger.info(f"Attempting pairing in {mode} mode …")
            pairs = self._score_and_match(members, strict=strict)
            if pairs:
                logger.info(f"Pairing succeeded in {mode} mode: {len(pairs)} group(s)")
                self._log_pairs(pairs)
                return pairs

        # Absolute fallback
        logger.warning("Falling back to random pairing.")
        pairs = self._random_pair(members)
        self._log_pairs(pairs)
        return pairs

    # ── Scoring ────────────────────────────────────────────────────────────────

    def _get_info(self, user_id: str) -> Dict[str, str]:
        if user_id in self.roster.index:
            row = self.roster.loc[user_id]
            return {
                "designation": str(row.get("designation", "unknown")).strip().lower(),
                "office": str(row.get("office", "unknown")).strip().lower(),
            }
        return {"designation": "unknown", "office": "unknown"}

    def _score(self, u1: str, u2: str, strict: bool = True) -> float:
        i1, i2 = self._get_info(u1), self._get_info(u2)
        score = 0.0

        # Repeat penalty (very high — avoids repeats unless unavoidable)
        if frozenset([u1, u2]) in self.historical_pairs:
            score += self.SCORE_REPEAT_PAIR_PENALTY

        # Designation
        if i1["designation"] != i2["designation"]:
            score += self.SCORE_CROSS_DESIGNATION
        elif strict:
            score += self.SCORE_SAME_DESIGNATION_PENALTY

        # Office
        if i1["office"] != i2["office"]:
            score += self.SCORE_CROSS_OFFICE
        elif strict:
            score += self.SCORE_SAME_OFFICE_PENALTY

        # Small jitter so deterministic inputs still produce varied pairings
        score += random.uniform(0, 0.5)

        return score

    # ── Matching ───────────────────────────────────────────────────────────────

    def _score_and_match(self, members: List[str], strict: bool) -> List[List[str]]:
        """
        Build a score matrix for all candidate pairs, then greedily pick
        the highest-scoring pairs one by one (each member used at most once).
        The final lone member in an odd list is appended to the last pair.
        """
        # Build & sort all candidate pairs by score (desc)
        candidates: List[Tuple[float, str, str]] = []
        for i, u1 in enumerate(members):
            for j, u2 in enumerate(members):
                if i < j:
                    candidates.append((self._score(u1, u2, strict=strict), u1, u2))

        candidates.sort(key=lambda x: x[0], reverse=True)

        paired: Set[str] = set()
        result: List[List[str]] = []

        for _, u1, u2 in candidates:
            if u1 not in paired and u2 not in paired:
                result.append([u1, u2])
                paired.update([u1, u2])
            if len(paired) >= len(members) - 1:  # at most 1 left unmatched
                break

        # Handle the odd-one-out
        remaining = [m for m in members if m not in paired]
        if remaining:
            if result:
                result[-1].extend(remaining)   # make last group a trio
            else:
                result.append(remaining)        # safety: whole group is the trio

        return result

    def _random_pair(self, members: List[str]) -> List[List[str]]:
        shuffled = list(members)
        random.shuffle(shuffled)
        result: List[List[str]] = []

        while len(shuffled) > 3:
            result.append([shuffled.pop(), shuffled.pop()])
        if len(shuffled) == 3:
            result.append(shuffled)
        elif len(shuffled) == 2:
            result.append(shuffled)
        elif len(shuffled) == 1 and result:
            result[-1].append(shuffled[0])

        return result

    # ── Logging helpers ────────────────────────────────────────────────────────

    def _log_pairs(self, pairs: List[List[str]]):
        for i, p in enumerate(pairs, 1):
            infos = [
                f"{uid} ({self._get_info(uid)['designation']} / {self._get_info(uid)['office']})"
                for uid in p
            ]
            label = "TRIO" if len(p) == 3 else "PAIR"
            logger.info(f"  Group {i} [{label}]: {' ↔ '.join(infos)}")
