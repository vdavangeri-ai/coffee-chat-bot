"""
run.py — Entry point for Coffee Chat Bot.

Usage:
  # Run once immediately (for cron jobs):
  python run.py --action pair          # Run monthly pairing
  python run.py --action check         # Run daily reminders/archiving
  python run.py --action both          # Run both

  # Run as a long-running scheduler (auto mode):
  python run.py --schedule             # Pairs on 1st of month at 09:00, checks daily

Environment variables (or use .env file):
  SLACK_BOT_TOKEN   — Your Slack Bot OAuth token (xoxb-...)
  ROSTER_PATH       — Path to your CSV / Excel roster file
  ANALYTICS_CHANNEL — Source channel name (default: analytics-all)
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

# Support .env files (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from bot import CoffeeChatBot

# ── Logging setup ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("coffee_chat_bot.log"),
    ],
)
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def build_bot() -> CoffeeChatBot:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    roster = os.environ.get("ROSTER_PATH", "roster.csv")
    channel = os.environ.get("ANALYTICS_CHANNEL", "analytics-all")

    if not token:
        logger.error(
            "SLACK_BOT_TOKEN is not set. "
            "Export it as an environment variable or add it to a .env file."
        )
        sys.exit(1)

    if not os.path.exists(roster):
        logger.error(
            f"Roster file not found: {roster}. "
            f"Set ROSTER_PATH to the correct path."
        )
        sys.exit(1)

    return CoffeeChatBot(bot_token=token, roster_path=roster, source_channel=channel)


def run_once(action: str):
    bot = build_bot()
    if action in ("pair", "both"):
        bot.run_monthly_pairing()
    if action in ("check", "both"):
        bot.run_daily_checks()


def run_scheduler():
    """
    Long-running scheduler.
      - Daily checks run every day at 09:00 local time.
      - Monthly pairing runs on the 1st of each month at 09:00.
    Uses a simple sleep-based loop (no external dependency beyond the stdlib).
    """
    try:
        import schedule
        _run_with_schedule()
    except ImportError:
        logger.warning(
            "The 'schedule' package is not installed — falling back to the built-in scheduler. "
            "Install it with:  pip install schedule"
        )
        _run_builtin_scheduler()


def _run_with_schedule():
    import schedule

    bot = build_bot()

    def daily_job():
        bot.run_daily_checks()

    def monthly_job():
        if datetime.now().day == 1:
            bot.run_monthly_pairing()

    schedule.every().day.at("09:00").do(daily_job)
    schedule.every().day.at("09:00").do(monthly_job)

    logger.info("Scheduler started (using 'schedule' library). Waiting for jobs …")
    while True:
        schedule.run_pending()
        time.sleep(60)


def _run_builtin_scheduler():
    """Minimal built-in scheduler — checks once a minute."""
    bot = build_bot()
    last_daily_date = None
    last_monthly_month = None

    logger.info("Scheduler started (built-in). Waiting for jobs …")
    while True:
        now = datetime.now()
        today = now.date()
        this_month = now.strftime("%Y-%m")

        if now.hour == 9 and now.minute == 0:
            if last_daily_date != today:
                logger.info("Running daily checks …")
                bot.run_daily_checks()
                last_daily_date = today

            if now.day == 1 and last_monthly_month != this_month:
                logger.info("Running monthly pairing …")
                bot.run_monthly_pairing()
                last_monthly_month = this_month

        time.sleep(60)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Coffee Chat Bot — automated Slack pairing for your team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--action",
        choices=["pair", "check", "both"],
        help="Run once: 'pair' for monthly pairing, 'check' for reminders/archiving, 'both' for both",
    )
    group.add_argument(
        "--schedule",
        action="store_true",
        help="Run as a long-running scheduler (recommended for production)",
    )

    # Optional overrides (supplement / override env vars)
    parser.add_argument("--token", help="Slack Bot Token (overrides SLACK_BOT_TOKEN env var)")
    parser.add_argument("--roster", help="Roster file path (overrides ROSTER_PATH env var)")
    parser.add_argument("--channel", help="Source channel (overrides ANALYTICS_CHANNEL env var)")

    args = parser.parse_args()

    # Apply CLI overrides to environment
    if args.token:
        os.environ["SLACK_BOT_TOKEN"] = args.token
    if args.roster:
        os.environ["ROSTER_PATH"] = args.roster
    if args.channel:
        os.environ["ANALYTICS_CHANNEL"] = args.channel

    if args.schedule:
        run_scheduler()
    else:
        run_once(args.action)


if __name__ == "__main__":
    main()
