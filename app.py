"""
app.py — Coffee Chat Bot: Streamlit Dashboard

A web UI for running, monitoring, and managing the Coffee Chat Bot.
"""

import io
import json
import logging
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="☕ Coffee Chat Bot",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
  }

  /* Background */
  .stApp {
    background: linear-gradient(135deg, #fdf6ec 0%, #fff9f2 60%, #fef3e2 100%);
  }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2c1810 0%, #4a2c1a 100%);
    border-right: none;
  }
  section[data-testid="stSidebar"] * {
    color: #f5e6d3 !important;
  }
  section[data-testid="stSidebar"] .stTextInput > div > div > input,
  section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    color: #f5e6d3 !important;
    border-radius: 8px;
  }
  section[data-testid="stSidebar"] label {
    color: #d4a978 !important;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  /* Hero title */
  .hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3rem;
    color: #2c1810;
    line-height: 1.1;
    margin-bottom: 0.2rem;
  }
  .hero-sub {
    font-size: 1.05rem;
    color: #7a5c44;
    font-weight: 300;
    margin-bottom: 2rem;
  }

  /* Cards */
  .stat-card {
    background: white;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 2px 16px rgba(44,24,16,0.07);
    border: 1px solid #f0dfc8;
    margin-bottom: 1rem;
  }
  .stat-card .stat-num {
    font-family: 'DM Serif Display', serif;
    font-size: 2.6rem;
    color: #c0580e;
    line-height: 1;
  }
  .stat-card .stat-label {
    font-size: 0.78rem;
    color: #9a7a62;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.3rem;
  }

  /* Section cards */
  .section-card {
    background: white;
    border-radius: 20px;
    padding: 2rem;
    box-shadow: 0 2px 20px rgba(44,24,16,0.07);
    border: 1px solid #f0dfc8;
    margin-bottom: 1.5rem;
  }
  .section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: #2c1810;
    margin-bottom: 0.4rem;
  }
  .section-desc {
    font-size: 0.9rem;
    color: #9a7a62;
    margin-bottom: 1.2rem;
  }

  /* Status badges */
  .badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .badge-green  { background: #e8f7ee; color: #1d7a42; }
  .badge-orange { background: #fff3e0; color: #c0580e; }
  .badge-red    { background: #fdecea; color: #b91c1c; }
  .badge-gray   { background: #f3f0ec; color: #7a5c44; }
  .badge-blue   { background: #e8f0fe; color: #1a56d6; }

  /* Timeline item */
  .timeline-item {
    display: flex;
    gap: 1rem;
    padding: 0.9rem 0;
    border-bottom: 1px solid #f5ece0;
  }
  .timeline-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #c0580e;
    margin-top: 0.35rem;
    flex-shrink: 0;
  }
  .timeline-text { font-size: 0.88rem; color: #4a3020; }
  .timeline-time { font-size: 0.75rem; color: #b09070; margin-top: 0.2rem; }

  /* Custom button overrides */
  .stButton > button {
    background: #c0580e !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.2s !important;
  }
  .stButton > button:hover {
    background: #a04a0c !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(192,88,14,0.35) !important;
  }
  .stButton > button[kind="secondary"] {
    background: white !important;
    color: #c0580e !important;
    border: 1.5px solid #c0580e !important;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: transparent;
    border-bottom: 2px solid #f0dfc8;
    padding-bottom: 0;
  }
  .stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500;
    font-size: 0.9rem;
    color: #9a7a62;
    border-radius: 8px 8px 0 0;
    padding: 0.5rem 1.2rem;
    border: none !important;
    background: transparent !important;
  }
  .stTabs [aria-selected="true"] {
    color: #c0580e !important;
    border-bottom: 2px solid #c0580e !important;
    font-weight: 600 !important;
  }

  /* Alerts */
  .stAlert {
    border-radius: 12px !important;
  }

  /* Divider */
  hr { border-color: #f0dfc8; }

  /* Hide Streamlit branding */
  #MainMenu, footer { visibility: hidden; }

  /* Log output */
  .log-box {
    background: #1a0e08;
    color: #d4a978;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    line-height: 1.7;
    max-height: 320px;
    overflow-y: auto;
    white-space: pre-wrap;
  }

  /* Info box */
  .info-box {
    background: linear-gradient(135deg, #fff8f2, #fff3e8);
    border: 1px solid #f0dfc8;
    border-left: 4px solid #c0580e;
    border-radius: 0 12px 12px 0;
    padding: 0.9rem 1.1rem;
    font-size: 0.88rem;
    color: #4a3020;
    margin: 0.8rem 0;
  }

  /* Channel row */
  .channel-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.8rem 1rem;
    background: #fdfaf6;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    border: 1px solid #f0e4d0;
  }
  .channel-name { font-weight: 600; color: #2c1810; font-size: 0.9rem; }
  .channel-meta { font-size: 0.78rem; color: #9a7a62; margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)


# ── Logging capture ────────────────────────────────────────────────────────────
class StreamlitLogHandler(logging.Handler):
    """Captures log output into a string list for display in the UI."""
    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record):
        self.records.append(self.format(record))

    def get_output(self) -> str:
        return "\n".join(self.records)

    def clear(self):
        self.records = []


_log_handler = StreamlitLogHandler()
_log_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s",
                                             datefmt="%H:%M:%S"))
logging.getLogger().addHandler(_log_handler)
logging.getLogger().setLevel(logging.INFO)

# ── Lazy imports (only load Slack modules once configured) ─────────────────────
@st.cache_resource(show_spinner=False)
def _get_bot(token: str, roster_bytes: bytes, roster_name: str, channel: str):
    """Instantiate the bot. Cached by token so it's not recreated on every rerun."""
    import tempfile
    from bot import CoffeeChatBot

    suffix = ".xlsx" if roster_name.endswith((".xlsx", ".xls")) else ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(roster_bytes)
        roster_path = f.name

    return CoffeeChatBot(bot_token=token, roster_path=roster_path, source_channel=channel)


# ── Session state defaults ─────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "configured": False,
        "bot_token": "",
        "channel": "analytics-all",
        "roster_bytes": None,
        "roster_name": "",
        "run_log": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── Storage helpers ────────────────────────────────────────────────────────────
def _read_storage() -> dict:
    """Always read live from GitHub (or disk fallback)."""
    from storage import Storage
    return Storage().data


def _storage_backend_label() -> str:
    from storage import _github_creds
    return "GitHub 🟢" if _github_creds() else "Local only 🔴 (resets on reboot)"


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ☕ Coffee Chat Bot")
    st.markdown("---")

    st.markdown("**🔑 Slack Bot Token**")
    token_input = st.text_input(
        "Token", type="password", placeholder="xoxb-...",
        value=st.session_state.bot_token,
        help="Your Slack Bot OAuth Token (starts with xoxb-)",
        label_visibility="collapsed",
    )

    st.markdown("**📢 Source Channel**")
    channel_input = st.text_input(
        "Channel", placeholder="analytics-all",
        value=st.session_state.channel,
        help="The Slack channel whose members will be paired",
        label_visibility="collapsed",
    )

    st.markdown("**📋 Employee Roster**")
    roster_file = st.file_uploader(
        "Upload roster", type=["csv", "xlsx", "xls"],
        help="CSV or Excel with columns: slack_user_id, designation, office",
        label_visibility="collapsed",
    )

    if st.button("✅ Save Configuration", use_container_width=True):
        if not token_input:
            st.error("Please enter your Slack Bot Token.")
        elif not roster_file:
            st.error("Please upload your employee roster.")
        else:
            st.session_state.bot_token = token_input
            st.session_state.channel = channel_input.strip().lstrip("#") or "analytics-all"
            st.session_state.roster_bytes = roster_file.read()
            st.session_state.roster_name = roster_file.name
            st.session_state.configured = True
            _get_bot.clear()
            st.success("Configuration saved!")
            st.rerun()

    st.markdown("---")
    st.markdown("**💾 Memory Storage**")
    backend_label = _storage_backend_label()
    st.caption(f"Backend: {backend_label}")
    if "Local only" in backend_label:
        st.warning("⚠️ Add GitHub secrets to make memory permanent — see Setup Guide.")


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='hero-title'>☕ Coffee Chat Bot</div>
<div class='hero-sub'>Automated team pairing · Monthly coffee chats · Slack-native</div>
""", unsafe_allow_html=True)

if not st.session_state.configured:
    st.markdown("""
    <div class='info-box'>
    👈 <strong>Get started:</strong> Fill in your Slack Bot Token, upload your employee roster,
    and click <em>Save Configuration</em> in the sidebar.
    </div>
    """, unsafe_allow_html=True)


# ── Stats bar ──────────────────────────────────────────────────────────────────
storage_data = _read_storage()
active_channels = {cid: v for cid, v in storage_data.get("active_channels", {}).items()
                   if not v.get("archived")}
total_months = len(storage_data.get("pairs_history", {}))
total_pairs = sum(len(p) for p in storage_data.get("pairs_history", {}).values())
pending_reminder = sum(1 for v in active_channels.values()
                       if not v.get("reminded") and
                       (datetime.now() - datetime.fromisoformat(v["created_at"])).days >= 5)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div class='stat-card'>
        <div class='stat-num'>{total_months}</div>
        <div class='stat-label'>Months Run</div></div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class='stat-card'>
        <div class='stat-num'>{total_pairs}</div>
        <div class='stat-label'>Total Pairs Made</div></div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div class='stat-card'>
        <div class='stat-num'>{len(active_channels)}</div>
        <div class='stat-label'>Active Chats</div></div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class='stat-card'>
        <div class='stat-num'>{pending_reminder}</div>
        <div class='stat-label'>Need Reminder</div></div>""", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Overview", "🎲 Run Pairing", "🔔 Daily Checks", "📜 History", "📋 Roster Preview"
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Overview
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    col_a, col_b = st.columns([1.3, 1])

    with col_a:
        st.markdown("<div class='section-title'>Active Coffee Chats</div>", unsafe_allow_html=True)
        if not active_channels:
            st.info("No active coffee chat channels right now. Run a pairing to get started!")
        else:
            for cid, info in active_channels.items():
                created = datetime.fromisoformat(info["created_at"])
                days_old = (datetime.now() - created).days
                reminded = info.get("reminded", False)
                members_str = "  ·  ".join(f"`{m}`" for m in info["members"])

                if days_old >= 10:
                    badge = "<span class='badge badge-red'>⚠️ Closing Soon</span>"
                elif reminded:
                    badge = "<span class='badge badge-orange'>⏰ Reminded</span>"
                else:
                    badge = "<span class='badge badge-green'>✅ Active</span>"

                st.markdown(f"""
                <div class='channel-row'>
                  <div>
                    <div class='channel-name'>#{cid}</div>
                    <div class='channel-meta'>{members_str}</div>
                  </div>
                  <div style='text-align:right'>
                    {badge}
                    <div class='channel-meta'>Day {days_old} of 15</div>
                  </div>
                </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div class='section-title'>How It Works</div>", unsafe_allow_html=True)
        steps = [
            ("🎲", "Day 0", "Pairs are created. Private Slack channels made. Welcome + ice-breaker message sent."),
            ("⏰", "Day 5", "If chat hasn't happened yet, a friendly reminder is sent."),
            ("🏁", "Day 15", "Closing message posted. Channel archived. See you next month!"),
        ]
        for icon, day, desc in steps:
            st.markdown(f"""
            <div class='timeline-item'>
              <div class='timeline-dot'></div>
              <div>
                <div class='timeline-text'><strong>{icon} {day}</strong> — {desc}</div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Pairing Rules</div>", unsafe_allow_html=True)
        rules = [
            ("Cross Designation", "Analyst ≠ Analyst"),
            ("Cross Office", "Different locations"),
            ("No Repeats", "Memory across months"),
            ("Odd Numbers", "One group of 3"),
            ("Rule Relaxation", "Fallback if needed"),
        ]
        for rule, detail in rules:
            st.markdown(f"""
            <div class='timeline-item'>
              <div class='timeline-dot'></div>
              <div class='timeline-text'><strong>{rule}</strong> — {detail}</div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Run Pairing
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("<div class='section-title'>🎲 Monthly Pairing</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-desc'>Creates this month's coffee chat pairs and sets up private Slack channels.</div>", unsafe_allow_html=True)

    month_key = datetime.now().strftime("%Y-%m")
    already_run = storage_data.get("pairs_history", {}).get(month_key)

    if already_run:
        st.warning(
            f"⚠️ Pairing has already been run for **{month_key}** "
            f"({len(already_run)} pairs created). "
            "Running again will be skipped unless you clear history."
        )

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div class='info-box'>
        📅 <strong>This Month:</strong> {datetime.now().strftime('%B %Y')}<br>
        📢 <strong>Source Channel:</strong> #{st.session_state.channel}<br>
        🔒 <strong>Status:</strong> {'Already run ✅' if already_run else 'Ready to run 🟢'}
        </div>
        """, unsafe_allow_html=True)

        run_pairing_btn = st.button(
            "🚀 Run Monthly Pairing",
            disabled=not st.session_state.configured,
            use_container_width=True,
        )

        if not st.session_state.configured:
            st.caption("⬅️ Configure the bot in the sidebar first.")

    with col2:
        if run_pairing_btn:
            if not st.session_state.configured:
                st.error("Please configure the bot in the sidebar first.")
            else:
                _log_handler.clear()
                with st.spinner("Running pairing — this may take a minute…"):
                    try:
                        bot = _get_bot(
                            st.session_state.bot_token,
                            st.session_state.roster_bytes,
                            st.session_state.roster_name,
                            st.session_state.channel,
                        )
                        bot.run_monthly_pairing()
                        st.success("✅ Monthly pairing complete! Check your Slack workspace.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

                log_output = _log_handler.get_output()
                if log_output:
                    st.markdown("<div class='log-box'>" + log_output.replace("\n", "<br>") + "</div>",
                                unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='info-box'>
            <strong>What happens when you click Run?</strong><br><br>
            1️⃣ Bot reads your roster file for designations & offices<br>
            2️⃣ Fetches current members from <code>#analytics-all</code><br>
            3️⃣ Builds smart pairs using cross-team rules<br>
            4️⃣ Creates private <code>#coffee-chat-YYYY-MM-N</code> channels<br>
            5️⃣ Posts ice-breaker welcome message in each channel<br>
            6️⃣ Saves pairs to memory (no repeats next month)
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Daily Checks
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("<div class='section-title'>🔔 Daily Maintenance</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-desc'>Sends reminders on day 5 and archives channels on day 15.</div>",
                unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div class='info-box'>
        🔔 <strong>Need Reminder:</strong> {pending_reminder} channel(s)<br>
        📦 <strong>Active Channels:</strong> {len(active_channels)}<br>
        </div>
        """, unsafe_allow_html=True)

        run_checks_btn = st.button(
            "⚡ Run Daily Checks",
            disabled=not st.session_state.configured,
            use_container_width=True,
        )

        if not st.session_state.configured:
            st.caption("⬅️ Configure the bot in the sidebar first.")

    with col2:
        if run_checks_btn:
            if not st.session_state.configured:
                st.error("Please configure the bot in the sidebar first.")
            else:
                _log_handler.clear()
                with st.spinner("Running daily checks…"):
                    try:
                        bot = _get_bot(
                            st.session_state.bot_token,
                            st.session_state.roster_bytes,
                            st.session_state.roster_name,
                            st.session_state.channel,
                        )
                        bot.run_daily_checks()
                        st.success("✅ Daily checks complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

                log_output = _log_handler.get_output()
                if log_output:
                    st.markdown("<div class='log-box'>" + log_output.replace("\n", "<br>") + "</div>",
                                unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='info-box'>
            <strong>What does this check?</strong><br><br>
            ⏰ <strong>Day 5+, not reminded yet</strong> → Sends a friendly nudge<br>
            🏁 <strong>Day 15+, not archived yet</strong> → Posts closing message and archives channel<br><br>
            <em>Run this daily (via cron or scheduler) for automatic management.</em>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🕐 Automate with Cron (optional)")
    st.code("""
# Add to your crontab (run: crontab -e)

# Monthly pairing — 1st of every month at 9am
0 9 1 * * curl -X POST https://your-streamlit-url/run?action=pair

# Daily checks — every day at 9am
0 9 * * * curl -X POST https://your-streamlit-url/run?action=check
    """, language="bash")
    st.caption("Or simply bookmark this page and click the buttons manually each month.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — History
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("<div class='section-title'>📜 Pairing History</div>", unsafe_allow_html=True)
    history = storage_data.get("pairs_history", {})

    if not history:
        st.info("No pairing history yet. Run your first monthly pairing!")
    else:
        for month, pairs in sorted(history.items(), reverse=True):
            with st.expander(f"📅 {month}  —  {len(pairs)} pair(s)", expanded=(month == month_key)):
                for i, group in enumerate(pairs, 1):
                    label = "👥 Pair" if len(group) == 2 else "👥👤 Trio"
                    members_str = "  ↔  ".join(f"`{m}`" for m in group)
                    st.markdown(f"**{label} {i}:** {members_str}")

    st.markdown("---")
    st.markdown("#### All Channels (incl. archived)")
    all_channels = storage_data.get("active_channels", {})
    if not all_channels:
        st.info("No channels created yet.")
    else:
        rows = []
        for cid, info in all_channels.items():
            created = datetime.fromisoformat(info["created_at"]).strftime("%Y-%m-%d %H:%M")
            rows.append({
                "Channel ID": cid,
                "Members": ", ".join(info["members"]),
                "Created": created,
                "Reminded": "✅" if info.get("reminded") else "❌",
                "Archived": "✅" if info.get("archived") else "❌",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Roster Preview
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown("<div class='section-title'>📋 Roster Preview</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-desc'>Preview your uploaded employee roster and check for issues.</div>",
                unsafe_allow_html=True)

    if not st.session_state.roster_bytes:
        st.info("Upload a roster file in the sidebar to preview it here.")
        st.markdown("---")
        st.markdown("#### Sample Roster Format")
        sample = pd.DataFrame({
            "slack_user_id": ["U012AB3CD1", "U012AB3CD2", "U012AB3CD3", "U012AB3CD4"],
            "designation": ["Analyst", "Manager", "Senior Analyst", "Associate"],
            "office": ["Mumbai", "London", "Singapore", "Mumbai"],
        })
        st.dataframe(sample, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download Sample CSV",
            data=sample.to_csv(index=False),
            file_name="sample_roster.csv",
            mime="text/csv",
        )
    else:
        try:
            roster_bytes = st.session_state.roster_bytes
            name = st.session_state.roster_name
            if name.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(roster_bytes))
            else:
                df = pd.read_excel(io.BytesIO(roster_bytes))

            st.success(f"✅ {len(df)} employees loaded from `{name}`")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Employees", len(df))
            with col2:
                des_col = next((c for c in df.columns if "desig" in c.lower() or "role" in c.lower()), None)
                st.metric("Unique Designations", df[des_col].nunique() if des_col else "—")
            with col3:
                off_col = next((c for c in df.columns if "office" in c.lower() or "location" in c.lower()
                                or "city" in c.lower()), None)
                st.metric("Office Locations", df[off_col].nunique() if off_col else "—")

            st.markdown("---")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Quick validation
            issues = []
            id_col = next((c for c in df.columns if "id" in c.lower()), None)
            if id_col and df[id_col].duplicated().any():
                issues.append(f"⚠️ Duplicate Slack User IDs found!")
            if df.isnull().any().any():
                issues.append("⚠️ Some cells are empty — fill them for best results.")

            if issues:
                for issue in issues:
                    st.warning(issue)
            else:
                st.success("✅ No issues found in your roster!")

        except Exception as e:
            st.error(f"Could not read roster: {e}")
