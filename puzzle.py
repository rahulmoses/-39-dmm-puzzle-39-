import streamlit as st
import sqlite3, time, os
from datetime import datetime

st.set_page_config(page_title="DMM Puzzle Challenge", layout="centered", page_icon="🧩")

# ── DB SETUP ────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "leaderboard.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            moves INTEGER NOT NULL,
            seconds REAL NOT NULL,
            completed_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def save_score(name, moves, seconds):
    conn = get_db()
    conn.execute(
        "INSERT INTO leaderboard (name, moves, seconds, completed_at) VALUES (?, ?, ?, ?)",
        (name, moves, round(seconds, 2), datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, moves, seconds, completed_at FROM leaderboard ORDER BY seconds ASC LIMIT 50"
    ).fetchall()
    conn.close()
    return rows

def already_played(name):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM leaderboard WHERE LOWER(name)=LOWER(?)", (name,)).fetchone()
    conn.close()
    return row is not None

# ── PUZZLE DATA (verified solution, CP4 = last cell) ───────
GRID = [[1]*6 for _ in range(5)]
ROWS, COLS, TOTAL, MAX_CP = 5, 6, 30, 4
CPS = {1: (4,0), 2: (2,5), 3: (0,5), 4: (1,0)}
SOLUTION = [(4,0),(3,0),(2,0),(2,1),(3,1),(4,1),(4,2),(3,2),(2,2),(2,3),(3,3),(4,3),
            (4,4),(4,5),(3,5),(3,4),(2,4),(2,5),(1,5),(0,5),(0,4),(1,4),(1,3),(0,3),
            (0,2),(1,2),(1,1),(0,1),(0,0),(1,0)]

def cp_at(r, c):
    for n, (pr, pc) in CPS.items():
        if pr == r and pc == c:
            return n
    return None

def is_adjacent(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1

def valid_moves():
    if not st.session_state.path:
        return set()
    lr, lc = st.session_state.path[-1]
    moves = set()
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = lr+dr, lc+dc
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            if (nr, nc) not in st.session_state.visited:
                cp = cp_at(nr, nc)
                if cp is None or cp == st.session_state.next_cp:
                    moves.add((nr, nc))
    return moves

def try_move(r, c):
    cell = (r, c)
    if st.session_state.completed:
        return
    if cell in st.session_state.visited:
        idx = st.session_state.path.index(cell)
        if idx == len(st.session_state.path) - 2:
            undo_last()
        return
    if not st.session_state.path:
        if cp_at(r, c) != 1:
            st.session_state.message = "⚠️ Start at checkpoint 1!"
            return
        st.session_state.start_time = time.time()
    else:
        last = st.session_state.path[-1]
        if not is_adjacent(last, cell):
            st.session_state.message = "⚠️ Only adjacent moves allowed!"
            return
        cp = cp_at(r, c)
        if cp is not None and cp != st.session_state.next_cp:
            st.session_state.message = f"⚠️ Visit checkpoint {st.session_state.next_cp} first!"
            return
    st.session_state.path.append(cell)
    st.session_state.visited.add(cell)
    cp = cp_at(r, c)
    if cp == st.session_state.next_cp:
        st.session_state.next_cp += 1
    if len(st.session_state.visited) == TOTAL and st.session_state.next_cp == MAX_CP + 1:
        st.session_state.completed = True
        st.session_state.elapsed = time.time() - st.session_state.start_time
        st.session_state.message = "🎉 Puzzle complete!"
    elif st.session_state.next_cp <= MAX_CP:
        rem = TOTAL - len(st.session_state.visited)
        st.session_state.message = f"Head to checkpoint {st.session_state.next_cp} — {rem} cells left"
    else:
        rem = TOTAL - len(st.session_state.visited)
        st.session_state.message = f"Cover {rem} more cells!"

def undo_last():
    if not st.session_state.path:
        return
    cell = st.session_state.path.pop()
    cp = cp_at(*cell)
    if cp is not None and cp < st.session_state.next_cp:
        st.session_state.next_cp -= 1
    st.session_state.visited.discard(cell)
    st.session_state.completed = False
    if not st.session_state.path:
        st.session_state.message = "Click checkpoint 1 to begin"
    else:
        st.session_state.message = f"Go to checkpoint {st.session_state.next_cp}" if st.session_state.next_cp <= MAX_CP else "Cover remaining cells!"

def reset_game():
    st.session_state.path = []
    st.session_state.visited = set()
    st.session_state.next_cp = 1
    st.session_state.completed = False
    st.session_state.message = "Click checkpoint 1 to begin"
    st.session_state.start_time = None
    st.session_state.elapsed = 0
    st.session_state.score_saved = False

# ── SESSION STATE INIT ───────────────────────────────────────
for k, v in [("path",[]),("visited",set()),("next_cp",1),("completed",False),
              ("message","Click checkpoint 1 to begin"),("start_time",None),
              ("elapsed",0),("score_saved",False),("player_name",""),
              ("screen","name"),("show_solution",False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
div[data-testid="stButton"] > button {
    width: 56px !important; height: 56px !important;
    padding: 0 !important; border-radius: 10px !important;
    font-size: 18px !important; font-weight: 800 !important;
    line-height: 1 !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #ff4b4b !important;
    border-color: #ff4b4b !important; color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SCREEN 1: NAME ENTRY
# ══════════════════════════════════════════════════════════════
if st.session_state.screen == "name":
    st.title("🧩 DMM Puzzle Challenge")
    st.markdown("Connect **1 → 2 → 3 → 4** in order and cover all 30 cells to win!")
    st.divider()

    name = st.text_input("Enter your name to begin:", placeholder="Your name here...")
    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("▶ Start Puzzle", type="primary", use_container_width=True):
            if not name.strip():
                st.error("Please enter your name!")
            elif already_played(name.strip()):
                st.error(f"**{name.strip()}** has already completed the puzzle! Only one attempt per person.")
            else:
                st.session_state.player_name = name.strip()
                st.session_state.screen = "puzzle"
                reset_game()
                st.rerun()

    st.divider()
    st.subheader("🏆 Leaderboard")
    rows = get_leaderboard()
    if rows:
        medals = ["🥇","🥈","🥉"]
        for i, (n, moves, secs, ts) in enumerate(rows):
            mins = int(secs)//60; s = int(secs)%60
            medal = medals[i] if i < 3 else f"#{i+1}"
            st.markdown(f"{medal} **{n}** — ⏱ {mins}:{s:02d} &nbsp;|&nbsp; 🔢 {moves} moves &nbsp;|&nbsp; 🕐 {ts}")
    else:
        st.info("No scores yet — be the first to complete it!")

# ══════════════════════════════════════════════════════════════
# SCREEN 2: PUZZLE
# ══════════════════════════════════════════════════════════════
elif st.session_state.screen == "puzzle":
    st.title(f"🧩 DMM Puzzle — {st.session_state.player_name}")

    # Live timer
    if st.session_state.start_time and not st.session_state.completed:
        elapsed = time.time() - st.session_state.start_time
    else:
        elapsed = st.session_state.elapsed
    mins = int(elapsed)//60; secs = int(elapsed)%60

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⏱ Time", f"{mins}:{secs:02d}")
    c2.metric("✅ Visited", f"{len(st.session_state.visited)}/{TOTAL}")
    c3.metric("🎯 Next CP", "Done!" if st.session_state.next_cp > MAX_CP else st.session_state.next_cp)
    c4.metric("🔢 Moves", len(st.session_state.path))

    # Status
    if st.session_state.completed:
        st.success(st.session_state.message)
    elif "⚠️" in st.session_state.message:
        st.warning(st.session_state.message)
    else:
        st.info(st.session_state.message)

    # Control buttons
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("↩ Undo"):
            undo_last(); st.rerun()
    with b2:
        if st.button("↺ Reset"):
            reset_game(); st.rerun()
    with b3:
        if st.button("💡 Solution"):
            st.session_state.show_solution = not st.session_state.show_solution; st.rerun()
    with b4:
        if st.button("🏆 Board"):
            st.session_state.screen = "leaderboard"; st.rerun()

    # Solution hint
    if st.session_state.show_solution:
        dir_map = {}
        for i in range(len(SOLUTION)-1):
            r,c = SOLUTION[i]; nr,nc = SOLUTION[i+1]
            dir_map[(r,c)] = {(-1,0):"↑",(1,0):"↓",(0,-1):"←",(0,1):"→"}[(nr-r,nc-c)]
        step_map = {cell:i+1 for i,cell in enumerate(SOLUTION)}
        with st.expander("💡 Solution Path (arrows show direction)", expanded=True):
            for r in range(ROWS):
                cols = st.columns(COLS)
                for c in range(COLS):
                    cell=(r,c); cp=cp_at(r,c)
                    with cols[c]:
                        if cp:
                            st.markdown(f"**CP{cp}**")
                        else:
                            arrow = dir_map.get(cell,"■")
                            st.markdown(f"`{step_map[cell]:2d}`{arrow}")

    st.divider()
    st.caption("Click checkpoint **1** to start · Click adjacent cells to move · Green border = valid next move")

    # ── GRID ────────────────────────────────────────────────
    valid = valid_moves()
    cur = st.session_state.path[-1] if st.session_state.path else None

    for r in range(ROWS):
        cols = st.columns(COLS)
        for c in range(COLS):
            cell = (r, c)
            cp = cp_at(r, c)
            with cols[c]:
                # Determine label
                if cell == cur:
                    label = str(cp) if cp else "★"
                elif cell in st.session_state.visited:
                    label = str(cp) if cp else "●"
                elif cp:
                    label = str(cp)
                else:
                    label = " "

                kind = "primary" if (cell == cur or cell in st.session_state.visited or cp) else "secondary"

                if st.button(label, key=f"c_{r}_{c}", type=kind,
                             disabled=st.session_state.completed and cell not in st.session_state.visited):
                    try_move(r, c)
                    st.rerun()

    # ── SAVE SCORE ─────────────────────────────────────────
    if st.session_state.completed and not st.session_state.score_saved:
        save_score(st.session_state.player_name, len(st.session_state.path), st.session_state.elapsed)
        st.session_state.score_saved = True
        st.balloons()

    if st.session_state.completed:
        st.divider()
        mins2 = int(st.session_state.elapsed)//60; secs2 = int(st.session_state.elapsed)%60
        st.success(f"🎉 **{st.session_state.player_name}** finished in **{mins2}:{secs2:02d}** with **{len(st.session_state.path)} moves**!")
        if st.button("🏆 See Leaderboard", type="primary", use_container_width=True):
            st.session_state.screen = "leaderboard"; st.rerun()

    # Auto-refresh timer while playing
    if st.session_state.start_time and not st.session_state.completed:
        time.sleep(0.5)
        st.rerun()

# ══════════════════════════════════════════════════════════════
# SCREEN 3: LEADERBOARD
# ══════════════════════════════════════════════════════════════
elif st.session_state.screen == "leaderboard":
    st.title("🏆 DMM Puzzle Leaderboard")
    st.markdown("Top scores from all players — ranked by fastest time!")
    st.divider()

    rows = get_leaderboard()
    medals = ["🥇","🥈","🥉"]

    if rows:
        # Top 3 podium
        if len(rows) >= 1:
            st.subheader("🎖 Podium")
            pcols = st.columns(min(3, len(rows)))
            for i, (n, moves, secs, ts) in enumerate(rows[:3]):
                mins = int(secs)//60; s = int(secs)%60
                with pcols[i]:
                    st.metric(f"{medals[i]} {n}", f"{mins}:{s:02d}", f"{moves} moves")

        st.divider()
        st.subheader("📋 Full Rankings")
        for i, (n, moves, secs, ts) in enumerate(rows):
            mins = int(secs)//60; s = int(secs)%60
            medal = medals[i] if i < 3 else f"#{i+1}"
            cols = st.columns([1,3,2,2,2])
            cols[0].markdown(medal)
            cols[1].markdown(f"**{n}**")
            cols[2].markdown(f"⏱ {mins}:{s:02d}")
            cols[3].markdown(f"🔢 {moves} moves")
            cols[4].markdown(f"🕐 {ts}")
    else:
        st.info("No scores yet! Be the first to complete the puzzle.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↩ Back to Puzzle", use_container_width=True):
            st.session_state.screen = "puzzle"; st.rerun()
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
