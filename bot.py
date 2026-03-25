"""
bot.py — Core Coffee Chat Bot logic.

Handles:
  - Reading the analytics-all channel roster
  - Creating private coffee-chat channels
  - Posting welcome, reminder, and closing messages as "Coffee Chat Admin"
  - Archiving channels after 15 days
  - Delegating pairing logic to PairingEngine
"""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from pairing import PairingEngine
from storage import Storage

logger = logging.getLogger(__name__)

BOT_DISPLAY_NAME = "Coffee Chat Admin"
BOT_ICON_EMOJI = ":coffee:"
REMINDER_AFTER_DAYS = 5
ARCHIVE_AFTER_DAYS = 15


# ── Message Templates ──────────────────────────────────────────────────────────

def _welcome_message(mentions: str) -> str:
    return f"""\
☕ *Welcome to your Coffee Chat!* ☕

Hey {mentions}! I'm your *Coffee Chat Admin*, and I'm thrilled to pair you up this month! 🎉

This is your private space to connect, share ideas, and get to know each other.

*🗓️ Step 1 — Schedule a time*
Find a 30-minute slot that works for everyone and set up a quick virtual or in-person catch-up. \
A Zoom call, Teams meeting, or a coffee at the office — the format is entirely up to you!

*💬 Step 2 — Break the ice*
Here are some conversation starters to get things going:
• What's a project you're currently excited about?
• What's a skill you're building this year?
• Best career advice you've ever received?
• If you could swap roles for a day, whose would you pick — and why?
• What's a hidden talent or hobby your colleagues don't know about?

*✅ Step 3 — Share the love*
Drop a note here after your chat — a fun fact you learned, a new idea that came up, anything!

_I'll check back in 5 days. You have 15 days total. Enjoy your chat!_ 😊
"""


def _reminder_message(mentions: str) -> str:
    return f"""\
⏰ *Friendly Reminder!* ⏰

Hey {mentions}! Just checking in — have you had a chance to schedule your coffee chat yet? ☕

*You still have 10 days left* — plenty of time! A few quick ways to coordinate:
• Reply here with time slots that work for you
• DM each other to set something up
• Use a scheduling tool like Calendly

Even a quick 20-minute chat can spark great connections and ideas 💡. Don't miss it!
"""


def _closing_message() -> str:
    return """\
🏁 *Wrapping Up!* 🏁

This coffee chat channel is coming to a close for the month. \
We hope you had a great conversation and made a meaningful connection! ☕

*This channel will be archived shortly.* A brand-new coffee chat pairing awaits you next month — stay tuned!

See you next time! 👋✨
"""


# ── CoffeeChatBot ──────────────────────────────────────────────────────────────

class CoffeeChatBot:
    def __init__(self, bot_token: str, roster_path: str, source_channel: str = "analytics-all"):
        self.client = WebClient(token=bot_token)
        self.storage = Storage()
        self.roster_path = roster_path
        self.source_channel = source_channel.lstrip("#")

    # ─── Roster ───────────────────────────────────────────────────────────────

    def load_roster(self) -> pd.DataFrame:
        """
        Load the employee roster from a CSV or Excel file.

        Required columns (case-insensitive, flexible names):
            slack_user_id  — Slack member ID (e.g. U012AB3CD)
            designation    — Job title / role (e.g. Analyst, Manager)
            office         — Office location (e.g. Mumbai, London)
        """
        path = self.roster_path
        logger.info(f"Loading roster from {path}")

        if path.lower().endswith(".csv"):
            df = pd.read_csv(path)
        elif path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported roster format: {path}. Use .csv or .xlsx")

        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Flexible column mapping
        col_map: Dict[str, str] = {}
        for col in df.columns:
            if re.search(r"(slack.?user.?id|user.?id|member.?id)", col):
                col_map[col] = "slack_user_id"
            elif re.search(r"(desig|role|title|position)", col):
                col_map[col] = "designation"
            elif re.search(r"(office|location|city|site)", col):
                col_map[col] = "office"
        df = df.rename(columns=col_map)

        required = ["slack_user_id", "designation", "office"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Roster is missing required columns: {missing}. "
                f"Available columns: {list(df.columns)}"
            )

        df = df[required].dropna(subset=["slack_user_id"])
        df["slack_user_id"] = df["slack_user_id"].astype(str).str.strip()
        logger.info(f"Roster loaded: {len(df)} members")
        return df

    # ─── Slack Helpers ────────────────────────────────────────────────────────

    def _get_channel_id(self, name: str) -> Optional[str]:
        name = name.lstrip("#")
        cursor = None
        try:
            while True:
                kwargs: dict = {"types": "public_channel,private_channel", "limit": 200}
                if cursor:
                    kwargs["cursor"] = cursor
                result = self.client.conversations_list(**kwargs)
                for ch in result["channels"]:
                    if ch["name"] == name:
                        return ch["id"]
                cursor = result.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
        except SlackApiError as e:
            logger.error(f"Error listing channels: {e}")
        return None

    def _get_channel_members(self, channel_id: str) -> List[str]:
        members: List[str] = []
        cursor = None
        try:
            while True:
                kwargs: dict = {"channel": channel_id, "limit": 200}
                if cursor:
                    kwargs["cursor"] = cursor
                result = self.client.conversations_members(**kwargs)
                members.extend(result["members"])
                cursor = result.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
        except SlackApiError as e:
            logger.error(f"Error fetching members of {channel_id}: {e}")
            return []

        # Filter bots and deactivated accounts
        human = []
        for uid in members:
            try:
                info = self.client.users_info(user=uid)["user"]
                if not info.get("is_bot") and not info.get("deleted") and not info.get("is_app_user"):
                    human.append(uid)
            except SlackApiError:
                pass
        logger.info(f"Found {len(human)} human members in channel {channel_id}")
        return human

    def _user_display_name(self, user_id: str) -> str:
        try:
            u = self.client.users_info(user=user_id)["user"]
            return u.get("real_name") or u.get("name") or user_id
        except SlackApiError:
            return user_id

    def _post(self, channel_id: str, text: str):
        try:
            self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                username=BOT_DISPLAY_NAME,
                icon_emoji=BOT_ICON_EMOJI,
            )
        except SlackApiError as e:
            logger.error(f"Error posting to {channel_id}: {e}")

    # ─── Channel Lifecycle ────────────────────────────────────────────────────

    def _create_coffee_channel(
        self, members: List[str], month_key: str, index: int
    ) -> Optional[str]:
        channel_name = f"coffee-chat-{month_key}-{index + 1}"
        try:
            result = self.client.conversations_create(
                name=channel_name, is_private=True
            )
            channel_id: str = result["channel"]["id"]
            logger.info(f"Created channel #{channel_name} ({channel_id})")

            # Invite members (bot is already in the channel it created)
            self.client.conversations_invite(
                channel=channel_id, users=",".join(members)
            )
            return channel_id

        except SlackApiError as e:
            # If the name already exists, append a suffix and retry once
            if e.response.get("error") == "name_taken":
                alt_name = f"coffee-chat-{month_key}-{index + 1}-x"
                try:
                    result = self.client.conversations_create(
                        name=alt_name, is_private=True
                    )
                    channel_id = result["channel"]["id"]
                    self.client.conversations_invite(
                        channel=channel_id, users=",".join(members)
                    )
                    return channel_id
                except SlackApiError as e2:
                    logger.error(f"Retry failed for {alt_name}: {e2}")
            else:
                logger.error(f"Error creating channel {channel_name}: {e}")
        return None

    def _archive_channel(self, channel_id: str):
        try:
            self.client.conversations_archive(channel=channel_id)
            logger.info(f"Archived channel {channel_id}")
        except SlackApiError as e:
            logger.error(f"Error archiving {channel_id}: {e}")

    # ─── Main Workflows ───────────────────────────────────────────────────────

    def run_monthly_pairing(self):
        """
        Entry point for the monthly pairing job.
        Idempotent — safe to call multiple times in the same month.
        """
        month_key = datetime.now().strftime("%Y-%m")
        logger.info(f"=== Monthly Pairing — {month_key} ===")

        if self.storage.already_paired_this_month(month_key):
            logger.info(f"Pairing already completed for {month_key}. Skipping.")
            return

        # 1. Load the latest roster (captures new hires + departures)
        try:
            roster = self.load_roster()
        except Exception as e:
            logger.error(f"Failed to load roster: {e}")
            return

        # 2. Get current members of the source channel
        src_channel_id = self._get_channel_id(self.source_channel)
        if not src_channel_id:
            logger.error(f"Channel #{self.source_channel} not found.")
            return
        channel_members = self._get_channel_members(src_channel_id)

        # 3. Intersect with roster (only pair people whose info we have)
        roster_ids = set(roster["slack_user_id"].tolist())
        eligible = [m for m in channel_members if m in roster_ids]
        unmatched = [m for m in channel_members if m not in roster_ids]

        if unmatched:
            logger.warning(
                f"{len(unmatched)} channel member(s) not found in roster and will be skipped: {unmatched}"
            )
        if len(eligible) < 2:
            logger.error("Not enough eligible members to pair. Aborting.")
            return

        logger.info(f"Eligible members: {len(eligible)}")

        # 4. Run pairing
        historical = self.storage.get_historical_pairs()
        engine = PairingEngine(roster, historical)
        pairs = engine.create_pairs(eligible)

        if not pairs:
            logger.error("Pairing engine returned no pairs. Aborting.")
            return

        # 5. Create Slack channels & post welcome messages
        saved_pairs: List[List[str]] = []
        for i, group in enumerate(pairs):
            channel_id = self._create_coffee_channel(group, month_key, i)
            if channel_id:
                mentions = self._format_mentions(group)
                self._post(channel_id, _welcome_message(mentions))
                self.storage.add_active_channel(channel_id, group)
                saved_pairs.append(group)
            else:
                logger.warning(f"Skipping pair {group} — channel creation failed.")

        # 6. Persist pairings
        self.storage.add_month_pairs(month_key, saved_pairs)
        logger.info(f"Monthly pairing complete — {len(saved_pairs)} coffee chat(s) created.")

    def run_daily_checks(self):
        """
        Entry point for the daily maintenance job.
        Sends reminders on day 5 and archives channels on day 15.
        """
        logger.info("=== Daily Checks ===")
        now = datetime.now()
        active = self.storage.get_active_channels()

        if not active:
            logger.info("No active channels to check.")
            return

        for channel_id, info in active.items():
            created_at = datetime.fromisoformat(info["created_at"])
            days = (now - created_at).days
            members = info["members"]
            mentions = self._format_mentions(members)

            if days >= ARCHIVE_AFTER_DAYS and not info.get("archived"):
                logger.info(f"Archiving {channel_id} (day {days})")
                self._post(channel_id, _closing_message())
                self._archive_channel(channel_id)
                self.storage.mark_archived(channel_id)

            elif days >= REMINDER_AFTER_DAYS and not info.get("reminded"):
                logger.info(f"Sending reminder to {channel_id} (day {days})")
                self._post(channel_id, _reminder_message(mentions))
                self.storage.mark_reminded(channel_id)

        logger.info("Daily checks complete.")

    # ─── Utility ──────────────────────────────────────────────────────────────

    @staticmethod
    def _format_mentions(members: List[str]) -> str:
        mentions = [f"<@{m}>" for m in members]
        if len(mentions) == 1:
            return mentions[0]
        if len(mentions) == 2:
            return f"{mentions[0]} and {mentions[1]}"
        return ", ".join(mentions[:-1]) + f", and {mentions[-1]}"
