"""
storage.py — Persistent storage for Coffee Chat Bot.

Uses GitHub as the storage backend so data survives Streamlit Cloud
restarts and sleep cycles. The file `coffee_chat_storage.json` is
read from and written to your GitHub repository on every save.

Falls back to local file storage when GitHub credentials are not set
(useful for local development/testing).
"""

import base64
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib import request as urllib_request
from urllib.error import HTTPError

logger = logging.getLogger(__name__)

STORAGE_FILE = "coffee_chat_storage.json"
GITHUB_PATH  = "coffee_chat_storage.json"   # path inside the repo


def _empty_data() -> dict:
    return {"pairs_history": {}, "active_channels": {}}


# ── GitHub API helpers ─────────────────────────────────────────────────────────

def _github_request(method: str, url: str, token: str, body: dict = None):
    """Make a GitHub REST API call and return the parsed JSON response."""
    data = json.dumps(body).encode() if body else None
    req = urllib_request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 404:
            return None          # file not found — fresh start
        raise


def _github_creds() -> Optional[tuple[str, str, str]]:
    """
    Return (token, owner, repo) from environment / Streamlit secrets.
    Returns None if not configured.
    """
    # Try Streamlit secrets first (production), then env vars (local dev)
    try:
        import streamlit as st
        token = st.secrets.get("GITHUB_TOKEN", "")
        owner = st.secrets.get("GITHUB_OWNER", "")
        repo  = st.secrets.get("GITHUB_REPO",  "")
    except Exception:
        token = os.environ.get("GITHUB_TOKEN", "")
        owner = os.environ.get("GITHUB_OWNER", "")
        repo  = os.environ.get("GITHUB_REPO",  "")

    if token and owner and repo:
        return token, owner, repo
    return None


# ── Storage class ──────────────────────────────────────────────────────────────

class Storage:
    """
    Persists data to GitHub (preferred) or local file (fallback).

    GitHub mode:  reads/writes coffee_chat_storage.json in your repo.
    Local mode:   reads/writes coffee_chat_storage.json on disk.
    """

    def __init__(self):
        self._sha: Optional[str] = None    # GitHub file SHA (needed for updates)
        self.data = self._load()

    # ── Load ───────────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        creds = _github_creds()
        if creds:
            return self._load_from_github(*creds)
        return self._load_from_disk()

    def _load_from_github(self, token: str, owner: str, repo: str) -> dict:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{GITHUB_PATH}"
        logger.info(f"Loading storage from GitHub: {owner}/{repo}/{GITHUB_PATH}")
        try:
            resp = _github_request("GET", url, token)
            if resp is None:
                logger.info("No storage file in GitHub yet — starting fresh.")
                return _empty_data()
            self._sha = resp["sha"]
            content = base64.b64decode(resp["content"]).decode()
            logger.info("Storage loaded from GitHub successfully.")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load from GitHub: {e}. Starting fresh.")
            return _empty_data()

    def _load_from_disk(self) -> dict:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE) as f:
                logger.info("Storage loaded from local file.")
                return json.load(f)
        logger.info("No local storage file found — starting fresh.")
        return _empty_data()

    # ── Save ───────────────────────────────────────────────────────────────────

    def save(self):
        creds = _github_creds()
        if creds:
            self._save_to_github(*creds)
        else:
            self._save_to_disk()

    def _save_to_github(self, token: str, owner: str, repo: str):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{GITHUB_PATH}"
        content_b64 = base64.b64encode(
            json.dumps(self.data, indent=2).encode()
        ).decode()

        body: dict = {
            "message": f"chore: update coffee chat storage [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
            "content": content_b64,
        }
        if self._sha:
            body["sha"] = self._sha   # required when updating an existing file

        try:
            resp = _github_request("PUT", url, token, body)
            if resp and "content" in resp:
                self._sha = resp["content"]["sha"]   # update SHA for next write
                logger.info("Storage saved to GitHub.")
            else:
                logger.error(f"Unexpected GitHub response: {resp}")
        except Exception as e:
            logger.error(f"Failed to save to GitHub: {e}")
            logger.info("Falling back to local save.")
            self._save_to_disk()

    def _save_to_disk(self):
        with open(STORAGE_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
        logger.info("Storage saved to local file.")

    # ── Status ─────────────────────────────────────────────────────────────────

    def backend(self) -> str:
        """Return a human-readable label of which backend is active."""
        return "GitHub ✅" if _github_creds() else "Local file ⚠️ (will reset on reboot)"

    # ── Pairing History ────────────────────────────────────────────────────────

    def already_paired_this_month(self, month_key: str) -> bool:
        return month_key in self.data["pairs_history"]

    def add_month_pairs(self, month_key: str, pairs: List[List[str]]):
        self.data["pairs_history"][month_key] = [list(p) for p in pairs]
        self.save()
        logger.info(f"Saved {len(pairs)} pairs for {month_key}")

    def get_historical_pairs(self) -> Set[frozenset]:
        all_pairs: Set[frozenset] = set()
        for month_pairs in self.data["pairs_history"].values():
            for pair in month_pairs:
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
