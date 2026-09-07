"""
King of the Course
A Stableford points tracker, fines system, and photo gallery for a golf group.
Backend: Supabase (Postgres + Storage)
"""

import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client
import uuid

# ---------------------------------------------------------------------------
# PAGE CONFIG + THEME
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="King of the Course",
    page_icon="⛳",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --cream: #F5F1E8;
    --cream-card: #FBF9F3;
    --green: #1B3A2B;
    --green-deep: #14291E;
    --gold: #C9A227;
    --gold-soft: #E4C766;
    --ink: #20241F;
    --ink-soft: #5B6259;
    --line: #DAD4C4;
    --red: #A5402E;
}

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: var(--cream);
}

h1, h2, h3 {
    font-family: 'Fraunces', serif !important;
    color: var(--green);
}

/* Header banner */
.kotc-header {
    background: var(--green);
    color: var(--cream);
    padding: 28px 26px 34px;
    margin: -1rem -1rem 1.5rem -1rem;
    border-radius: 0 0 22px 22px;
}
.kotc-header h1 {
    color: var(--cream) !important;
    font-size: 32px;
    margin: 0;
}
.kotc-header p {
    color: #C9CFC4;
    margin: 6px 0 0 0;
    font-size: 14px;
}

/* Leaderboard rows */
.board-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 6px;
    border-bottom: 1px solid var(--line);
}
.board-row.top {
    background: linear-gradient(90deg, rgba(201,162,39,0.10), transparent);
    border-radius: 6px;
}
.rank-num {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    font-weight: 600;
    color: var(--ink-soft);
    width: 30px;
}
.board-row.top .rank-num { color: var(--gold); }

.avatar {
    width: 40px; height: 40px;
    border-radius: 50%;
    object-fit: cover;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--green);
    color: var(--cream);
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 14px;
    flex-shrink: 0;
}

.player-name { font-weight: 600; font-size: 16px; color: var(--ink); }
.player-meta { font-size: 12.5px; color: var(--ink-soft); }

.avg-num { font-family: 'Fraunces', serif; font-size: 20px; font-weight: 600; color: var(--ink); text-align: right; }
.avg-label { font-size: 11px; color: var(--ink-soft); text-align: right; }

.provisional {
    font-size: 10px; color: var(--gold); border: 1px solid var(--gold);
    border-radius: 3px; padding: 0px 5px; margin-left: 4px; font-weight: 600;
}

.kitty-hero {
    background: var(--green);
    color: var(--cream);
    padding: 26px;
    text-align: center;
    border-radius: 10px;
    margin-bottom: 20px;
}
.kitty-hero .amount { font-family: 'Fraunces', serif; font-size: 42px; font-weight: 600; color: var(--gold-soft); }
.kitty-hero .label { font-size: 13px; color: #C9CFC4; margin-top: 4px; }

.fine-preview {
    padding: 12px 14px;
    background: rgba(165,64,46,0.08);
    border-left: 3px solid var(--red);
    font-size: 14px;
    border-radius: 3px;
}
.fine-preview.rebate { background: rgba(27,58,43,0.08); border-left: 3px solid var(--green); }
.fine-preview.zero { background: rgba(91,98,89,0.08); border-left: 3px solid var(--ink-soft); }

hr { border-color: var(--line); }

/* Buttons */
.stButton>button {
    background-color: var(--green);
    color: var(--cream);
    border: none;
    font-weight: 600;
    border-radius: 4px;
}
.stButton>button:hover {
    background-color: var(--green-deep);
    color: var(--cream);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SUPABASE CONNECTION
# ---------------------------------------------------------------------------

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

PROFILE_BUCKET = "profile-photos"
GALLERY_BUCKET = "gallery-photos"

BEHAVIORAL_FINES = [
    ("ladies_tee_count", "Didn't hit it past the ladies' tee"),
    ("four_putt_count", "4-putt"),
    ("off_green_count", "Putting off the green"),
    ("bunker_count", "3+ shots in a bunker"),
]

AVATAR_COLORS = ["#1B3A2B", "#8a7326", "#6b4a3a", "#3a5240", "#9c5a3c", "#4a5d6b"]

# ---------------------------------------------------------------------------
# DATA ACCESS
# ---------------------------------------------------------------------------

@st.cache_data(ttl=15)
def get_players():
    res = supabase.table("players").select("*").order("name").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["id", "name", "photo_url"]
    )

@st.cache_data(ttl=15)
def get_rounds():
    res = supabase.table("rounds").select("*").order("round_date", desc=True).execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["id", "player_id", "round_date", "course", "handicap", "points",
                 "ladies_tee_count", "four_putt_count", "off_green_count",
                 "bunker_count", "created_at"]
    )
    if not df.empty:
        df["round_date"] = pd.to_datetime(df["round_date"])
    return df

@st.cache_data(ttl=15)
def get_monthly_fines():
    res = supabase.table("monthly_fines").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["id", "player_id", "month_label", "amount", "reason", "created_at"]
    )

@st.cache_data(ttl=15)
def get_gallery_photos():
    res = supabase.table("gallery_photos").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["id", "url", "caption", "created_at"]
    )

def clear_caches():
    get_players.clear()
    get_rounds.clear()
    get_monthly_fines.clear()
    get_gallery_photos.clear()

# ---------------------------------------------------------------------------
# FINE LOGIC
# ---------------------------------------------------------------------------

def score_based_fine(points: float) -> float:
    """Worst-tier-only score fine. Negative value = rebate."""
    if points < 15:
        return 40
    elif points < 20:
        return 20
    elif points < 30:
        return 10
    elif points >= 40:
        return -10
    return 0

def behavioral_fine(row) -> float:
    total = 0
    for col, _ in BEHAVIORAL_FINES:
        total += row.get(col, 0) * 10
    return total

def round_total_fine(row) -> float:
    return score_based_fine(row["points"]) + behavioral_fine(row)

def initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()

def avatar_color(player_id: str) -> str:
    idx = int(uuid.UUID(player_id).int) % len(AVATAR_COLORS) if is_valid_uuid(player_id) else 0
    return AVATAR_COLORS[idx]

def is_valid_uuid(val) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except Exception:
        return False

def render_avatar(name, photo_url, player_id, size=40):
    if photo_url:
        return f'<img src="{photo_url}" class="avatar" style="width:{size}px;height:{size}px;" />'
    color = avatar_color(str(player_id)) if player_id else "#1B3A2B"
    return (f'<div class="avatar" style="width:{size}px;height:{size}px;background:{color};">'
            f'{initials(name)}</div>')

# ---------------------------------------------------------------------------
# LEADERBOARD CALC
# ---------------------------------------------------------------------------

def build_leaderboard(players_df, rounds_df):
    rows = []
    for _, p in players_df.iterrows():
        p_rounds = rounds_df[rounds_df["player_id"] == p["id"]].sort_values("round_date", ascending=False)
        n = len(p_rounds)
        if n == 0:
            continue
        last5 = p_rounds.head(5)
        avg_pts = last5["points"].mean()
        latest_handicap = p_rounds.iloc[0]["handicap"]
        rows.append({
            "player_id": p["id"],
            "name": p["name"],
            "photo_url": p.get("photo_url"),
            "handicap": latest_handicap,
            "avg_points": round(avg_pts, 1),
            "rounds_played": n,
            "provisional": n < 5,
        })
    board = pd.DataFrame(rows)
    if not board.empty:
        board = board.sort_values("avg_points", ascending=False).reset_index(drop=True)
    return board

def build_fines_summary(players_df, rounds_df, monthly_df):
    rows = []
    for _, p in players_df.iterrows():
        p_rounds = rounds_df[rounds_df["player_id"] == p["id"]]
        round_fines_total = p_rounds.apply(round_total_fine, axis=1).sum() if not p_rounds.empty else 0
        p_monthly = monthly_df[monthly_df["player_id"] == p["id"]] if not monthly_df.empty else monthly_df
        monthly_total = p_monthly["amount"].sum() if not p_monthly.empty else 0
        net = round_fines_total + monthly_total
        latest_handicap = None
        if not p_rounds.empty:
            latest_handicap = p_rounds.sort_values("round_date", ascending=False).iloc[0]["handicap"]
        rows.append({
            "player_id": p["id"],
            "name": p["name"],
            "photo_url": p.get("photo_url"),
            "handicap": latest_handicap,
            "net_fines": net,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("net_fines", ascending=False).reset_index(drop=True)
    return df

# ---------------------------------------------------------------------------
# STORAGE HELPERS
# ---------------------------------------------------------------------------

def upload_photo(bucket: str, file, path_prefix: str) -> str:
    ext = file.name.split(".")[-1]
    path = f"{path_prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    file_bytes = file.getvalue()
    supabase.storage.from_(bucket).upload(
        path, file_bytes, {"content-type": file.type}
    )
    public_url = supabase.storage.from_(bucket).get_public_url(path)
    return public_url

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="kotc-header">
        <h1>King of the Course</h1>
        <p>Five-round averages, self-reported handicaps, and the kitty everyone pretends not to check.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# NAV
# ---------------------------------------------------------------------------

page = st.radio(
    "Navigate",
    ["Leaderboard", "Enter a Round", "History", "Fines & Kitty", "Photos", "Players"],
    horizontal=True,
    label_visibility="collapsed",
)

players_df = get_players()
rounds_df = get_rounds()
monthly_df = get_monthly_fines()
gallery_df = get_gallery_photos()

# ---------------------------------------------------------------------------
# PAGE: LEADERBOARD
# ---------------------------------------------------------------------------

if page == "Leaderboard":
    st.subheader("Leaderboard")
    st.caption("Ranked by average points, last 5 rounds")

    if players_df.empty:
        st.info("No players yet — add your mates on the Players tab.")
    else:
        board = build_leaderboard(players_df, rounds_df)
        if board.empty:
            st.info("No rounds logged yet — enter a round to get things started.")
        else:
            for i, row in board.iterrows():
                top_class = "top" if i == 0 else ""
                prov_html = '<span class="provisional">PROV</span>' if row["provisional"] else ""
                avatar_html = render_avatar(row["name"], row["photo_url"], row["player_id"])
                st.markdown(
                    f"""
                    <div class="board-row {top_class}">
                        <div style="display:flex;align-items:center;gap:14px;">
                            <div class="rank-num">{i+1}</div>
                            {avatar_html}
                            <div>
                                <div class="player-name">{row['name']}</div>
                                <div class="player-meta">Handicap {row['handicap']} · {row['rounds_played']} rounds {prov_html}</div>
                            </div>
                        </div>
                        <div>
                            <div class="avg-num">{row['avg_points']}</div>
                            <div class="avg-label">avg pts</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ---------------------------------------------------------------------------
# PAGE: ENTER A ROUND
# ---------------------------------------------------------------------------

elif page == "Enter a Round":
    st.subheader("Enter a Round")
    st.caption("Fine or rebate is calculated automatically")

    if players_df.empty:
        st.warning("Add at least one player on the Players tab first.")
    else:
        player_name = st.selectbox("Player", players_df["name"].tolist())
        player_id = players_df[players_df["name"] == player_name]["id"].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            round_date = st.date_input("Date", value=date.today())
        with col2:
            course = st.text_input("Course")

        col3, col4 = st.columns(2)
        with col3:
            handicap = st.number_input("Handicap", min_value=0.0, max_value=54.0, step=0.1, format="%.1f")
        with col4:
            points = st.number_input("Points scored", min_value=0, max_value=60, step=1)

        base_fine = score_based_fine(points)
        if base_fine > 0:
            st.markdown(f'<div class="fine-preview">${base_fine} fine — score-based</div>', unsafe_allow_html=True)
        elif base_fine < 0:
            st.markdown(f'<div class="fine-preview rebate">${abs(base_fine)} rebate — great round</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="fine-preview zero">No score-based fine or rebate</div>', unsafe_allow_html=True)

        st.markdown("**Additional fines ($10 each)**")
        counts = {}
        for col_key, label in BEHAVIORAL_FINES:
            counts[col_key] = st.number_input(label, min_value=0, max_value=10, step=1, key=col_key)

        behavioral_total = sum(v * 10 for v in counts.values())
        total_fine = base_fine + behavioral_total
        st.markdown(f"**Total for this round: ${total_fine}**" + (" (net rebate)" if total_fine < 0 else ""))

        if st.button("Save round", use_container_width=True):
            if not course:
                st.error("Please enter a course name.")
            else:
                supabase.table("rounds").insert({
                    "player_id": player_id,
                    "round_date": str(round_date),
                    "course": course,
                    "handicap": handicap,
                    "points": points,
                    **counts,
                }).execute()
                clear_caches()
                st.success(f"Round saved for {player_name}.")
                st.rerun()

# ---------------------------------------------------------------------------
# PAGE: HISTORY
# ---------------------------------------------------------------------------

elif page == "History":
    st.subheader("Round History")
    st.caption("All entries, most recent first")

    if rounds_df.empty:
        st.info("No rounds logged yet.")
    else:
        merged = rounds_df.merge(players_df, left_on="player_id", right_on="id", suffixes=("", "_p"))
        filter_name = st.selectbox("Filter by player", ["All"] + sorted(players_df["name"].tolist()))
        if filter_name != "All":
            merged = merged[merged["name"] == filter_name]

        merged["total_fine"] = merged.apply(round_total_fine, axis=1)

        for _, row in merged.sort_values("round_date", ascending=False).iterrows():
            avatar_html = render_avatar(row["name"], row.get("photo_url"), row["player_id"], size=30)
            fine = row["total_fine"]
            if fine > 0:
                tag = f'<span style="color:#A5402E;font-weight:600;">${fine}</span>'
            elif fine < 0:
                tag = f'<span style="color:#1B3A2B;font-weight:600;">-${abs(fine)}</span>'
            else:
                tag = '<span style="color:#5B6259;">—</span>'
            behav_notes = ", ".join(
                f"{count}× {label}" for col, label in BEHAVIORAL_FINES
                if (count := row.get(col, 0)) > 0
            )
            date_str = row["round_date"].strftime("%d %b")
            row_col, del_col = st.columns([9, 1])
            with row_col:
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                padding:12px 0;border-bottom:1px solid #DAD4C4;">
                        <div style="width:70px;">
                            <div style="font-size:12.5px;color:#5B6259;">{date_str}</div>
                            <div style="font-size:12px;color:#5B6259;">{row['course']}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:10px;flex:1;">
                            {avatar_html}
                            <div>
                                <div class="player-name">{row['name']}</div>
                                {f'<div style="font-size:11.5px;color:#5B6259;">{behav_notes}</div>' if behav_notes else ''}
                            </div>
                        </div>
                        <div class="avg-num" style="width:40px;">{row['points']}</div>
                        <div style="width:50px;text-align:right;">{tag}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with del_col:
                confirm_key = f"confirm_del_round_{row['id']}"
                if st.session_state.get(confirm_key):
                    if st.button("Confirm", key=f"confirm_btn_{row['id']}"):
                        supabase.table("rounds").delete().eq("id", row["id"]).execute()
                        clear_caches()
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"del_btn_{row['id']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()

# ---------------------------------------------------------------------------
# PAGE: FINES & KITTY
# ---------------------------------------------------------------------------

elif page == "Fines & Kitty":
    st.subheader("Fines & Kitty")

    if players_df.empty:
        st.info("No players yet.")
    else:
        summary = build_fines_summary(players_df, rounds_df, monthly_df)
        kitty_total = summary["net_fines"].sum() if not summary.empty else 0

        st.markdown(
            f"""
            <div class="kitty-hero">
                <div class="amount">${kitty_total:,.0f}</div>
                <div class="label">currently in the kitty</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Per player** — net of fines and rebates, all-time")
        for _, row in summary.iterrows():
            avatar_html = render_avatar(row["name"], row["photo_url"], row["player_id"])
            amt = row["net_fines"]
            amt_html = (f'<span style="color:#A5402E;">${amt:,.0f}</span>' if amt > 0
                        else f'<span style="color:#1B3A2B;">-${abs(amt):,.0f}</span>' if amt < 0
                        else '<span style="color:#5B6259;">$0</span>')
            hcp_str = f"Handicap {row['handicap']}" if pd.notna(row["handicap"]) else "No rounds yet"
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:12px 0;border-bottom:1px solid #DAD4C4;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        {avatar_html}
                        <div>
                            <div class="player-name">{row['name']}</div>
                            <div class="player-meta">{hcp_str}</div>
                        </div>
                    </div>
                    <div class="avg-num">{amt_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()
        with st.expander("Add a manual fine (e.g. didn't play this month)"):
            m_player = st.selectbox("Player", players_df["name"].tolist(), key="manual_player")
            m_reason = st.text_input("Reason", value="Didn't play this month")
            m_amount = st.number_input("Amount ($)", min_value=0, value=20, step=5)
            if st.button("Add fine"):
                m_player_id = players_df[players_df["name"] == m_player]["id"].iloc[0]
                supabase.table("monthly_fines").insert({
                    "player_id": m_player_id,
                    "month_label": date.today().strftime("%B %Y"),
                    "amount": m_amount,
                    "reason": m_reason,
                }).execute()
                clear_caches()
                st.success("Fine added.")
                st.rerun()

# ---------------------------------------------------------------------------
# PAGE: PHOTOS
# ---------------------------------------------------------------------------

elif page == "Photos":
    st.subheader("Photos")
    st.caption("No scoring logic here — just the good bits")

    with st.expander("+ Upload a photo"):
        photo_file = st.file_uploader("Choose a photo", type=["jpg", "jpeg", "png"])
        caption = st.text_input("Caption (optional)", key="gallery_caption")
        if photo_file and st.button("Upload"):
            url = upload_photo(GALLERY_BUCKET, photo_file, "gallery")
            supabase.table("gallery_photos").insert({
                "url": url,
                "caption": caption,
            }).execute()
            clear_caches()
            st.success("Photo uploaded.")
            st.rerun()

    if gallery_df.empty:
        st.info("No photos yet — be the first to upload one.")
    else:
        cols = st.columns(2)
        for i, row in gallery_df.iterrows():
            with cols[i % 2]:
                st.image(row["url"], use_container_width=True)
                if row.get("caption"):
                    st.caption(row["caption"])

# ---------------------------------------------------------------------------
# PAGE: PLAYERS
# ---------------------------------------------------------------------------

elif page == "Players":
    st.subheader("Players")
    st.caption("Add a mate, or update a profile photo")

    with st.expander("+ Add a mate"):
        new_name = st.text_input("Name")
        new_photo = st.file_uploader("Profile photo (optional)", type=["jpg", "jpeg", "png"], key="new_player_photo")
        if st.button("Add player"):
            if not new_name.strip():
                st.error("Enter a name.")
            elif new_name.strip() in players_df["name"].tolist():
                st.error("That player already exists.")
            else:
                photo_url = None
                if new_photo:
                    photo_url = upload_photo(PROFILE_BUCKET, new_photo, new_name.strip().replace(" ", "_"))
                supabase.table("players").insert({
                    "name": new_name.strip(),
                    "photo_url": photo_url,
                }).execute()
                clear_caches()
                st.success(f"Added {new_name.strip()}.")
                st.rerun()

    st.divider()

    if players_df.empty:
        st.info("No players yet.")
    else:
        for _, p in players_df.iterrows():
            avatar_html = render_avatar(p["name"], p.get("photo_url"), p["id"])
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:12px;padding:8px 0;">
                        {avatar_html}
                        <div class="player-name">{p['name']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                update_photo = st.file_uploader(
                    "Update photo", type=["jpg", "jpeg", "png"],
                    key=f"update_{p['id']}", label_visibility="collapsed"
                )
                if update_photo:
                    photo_url = upload_photo(PROFILE_BUCKET, update_photo, p["name"].replace(" ", "_"))
                    supabase.table("players").update({"photo_url": photo_url}).eq("id", p["id"]).execute()
                    clear_caches()
                    st.success("Photo updated.")
                    st.rerun()
            with col3:
                confirm_key = f"confirm_del_player_{p['id']}"
                if st.session_state.get(confirm_key):
                    round_count = len(rounds_df[rounds_df["player_id"] == p["id"]]) if not rounds_df.empty else 0
                    st.caption(f"Deletes {round_count} round(s) too")
                    if st.button("Confirm", key=f"confirm_pbtn_{p['id']}"):
                        supabase.table("players").delete().eq("id", p["id"]).execute()
                        clear_caches()
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"del_pbtn_{p['id']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
