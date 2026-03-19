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

# --- NEW: ADMIN RESET TOOL IN SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Admin Settings")
    st.write("Use this to restart the competition for the whole team.")
    if st.button("💣 WIPE ALL SCORES", help="This deletes the entire leaderboard forever!"):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DROP TABLE IF EXISTS leaderboard")
        conn.commit()
        conn.close()
        st.success("Database Deleted! Refreshing...")
        time.sleep(1)
        st.rerun()

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
        "SELECT name, moves, seconds, completed_at FROM leaderboard ORDER BY seconds ASC LIMIT 150"
    ).fetchall()
    conn.close()
    return rows

def already_played(name):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM leaderboard WHERE LOWER(name)=LOWER(?)", (name,)).fetchone()
    conn.close()
    return row is not None

# ── PUZZLE DATA ───────
ROWS, COLS, TOTAL, MAX_CP = 9, 8, 50, 6
CPS = {1:(0,0), 2:(7,1), 3:(6,4), 4:(4,5), 5:(1,3), 6:(0,7)}
SOLUTION = [(0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),(7,0),(8,0),(8,1),
            (7,1),(7,2),(7,3),(7,4),(7,5),(7,6),(7,7),(6,7),(6,6),(6,5),
            (6,4),(6,3),(6,2),(6,1),(5,1),(4,1),(4,2),(4,3),(4,4),(4,5),
            (3,5),(3,4),(3,3),(3,2),(3,1),(2,1),(1,1),(0,1),(0,2),(1,2),
            (1,3),(0,3),(0,4),(1,4),(1,5),(0,5),(0,6),(1,6),(1,7),(0,7)]

def cp_at(r, c):
    for n, (pr, pc) in CPS.items():
        if pr == r and pc == c: return n
    return None

def is_adjacent(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1

def valid_moves():
    if not st.session_state.path: return set()
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
    if st.session_state.completed: return
    if cell in st.session_state.visited:
        idx = st.session_state.path.index(cell)
        if idx == len(st.session_state.path) - 2: undo_last()
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
    
    # FIXED COMPLETION LOGIC: Checks for CP6 specifically
    if cp == MAX_CP and len(st.session_state.visited) == TOTAL:
        st.session_state.completed = True
        st.session_state.elapsed = time.time() - st.session_state.start_time
        st.session_state.message = "🎉 Puzzle complete!"
    else:
        rem = TOTAL - len(st.session_state.visited)
        st.session_state.message = f"Head to CP {st.session_state.next_cp} — {rem} cells left"

def undo_last():
    if not st.session_state.path: return
    cell = st.session_state.path.pop()
    cp = cp_at(*cell)
    if cp is not None and cp < st.session_state.next_cp:
        st.session_state.next_cp -= 1
    st.session_state.visited.discard(cell)
    st.session_state.completed = False
    st.session_state.message = f"Go to CP {st.session_state.next_cp}" if st.session_state.path else "Click CP 1 to begin"

def reset_game():
    st.session_state.update({"path":[], "visited":set(), "next_cp":1, "completed":False, 
                             "message":"Click CP 1 to begin", "start_time":None, "elapsed":0, "score_saved":False})

# ── SESSION STATE INIT ───────────────────────────────────────
for k, v in [("path",[]),("visited",set()),("next_cp",1),("completed",False),
              ("message","Click CP 1 to begin"),("start_time",None),
              ("elapsed",0),("score_saved",False),("player_name",""),
              ("screen","name"),("show_solution",False)]:
    if k not in st.session_state: st.session_state[k] = v

# ── CSS ─────────────────────────────────────────────────────
st.markdown("""<style>
div[data-testid="stButton"] > button { width: 56px !important; height: 56px !important; border-radius: 10px !important; font-weight: 800 !important; }
div[data-testid="stButton"] > button[kind="primary"] { background-color: #ff4b4b !important; color: white !important; }
</style>""", unsafe_allow_html=True)

# ── SCREEN 1: NAME ──────────────────────────────────────────
if st.session_state.screen == "name":
    st.title("🧩 DMM Puzzle Challenge")
    name = st.text_input("Enter your name:", placeholder="Your name here...")
    if st.button("▶ Start", type="primary", use_container_width=True):
        if name.strip() and not already_played(name.strip()):
            st.session_state.player_name = name.strip()
            st.session_state.screen = "puzzle"
            reset_game()
            st.rerun()
        elif already_played(name.strip()): st.error("Already played!")
    
    st.divider()
    st.subheader("🏆 Leaderboard")
    rows = get_leaderboard()
    for i, (n, m, s, ts) in enumerate(rows):
        st.markdown(f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'#{i+1}'} **{n}** — {int(s)//60}:{int(s)%60:02d} | {m} moves")

# ── SCREEN 2: PUZZLE ────────────────────────────────────────
elif st.session_state.screen == "puzzle":
    st.title(f"🧩 {st.session_state.player_name}")
    elapsed = (time.time() - st.session_state.start_time) if (st.session_state.start_time and not st.session_state.completed) else st.session_state.elapsed
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⏱ Time", f"{int(elapsed)//60}:{int(elapsed)%60:02d}")
    c2.metric("✅ Cells", f"{len(st.session_state.visited)}/{TOTAL}")
    c3.metric("🎯 Next", "Done!" if st.session_state.next_cp > MAX_CP else st.session_state.next_cp)
    c4.metric("🔢 Moves", len(st.session_state.path))

    if st.session_state.completed: st.success(st.session_state.message)
    else: st.info(st.session_state.message)

    b1, b2, b3, b4 = st.columns(4)
    with b1: 
        if st.button("↩ Undo"): undo_last(); st.rerun()
    with b2: 
        if st.button("↺ Reset"): reset_game(); st.rerun()
    with b3:
        if st.button("💡 Sol"): st.session_state.show_solution = not st.session_state.show_solution; st.rerun()
    with b4:
        if st.button("🏆 Board"): st.session_state.screen = "name"; st.rerun()

    if st.session_state.show_solution:
        with st.expander("💡 Solution Hint", expanded=True):
            st.write("Follow the CP order: 1 -> 5 -> 2 -> 3 -> 4 -> 6")

    # GRID
    for r in range(ROWS):
        cols = st.columns(COLS)
        for c in range(COLS):
            cell = (r, c); cp = cp_at(r, c)
            label = str(cp) if cp else ("★" if (st.session_state.path and cell == st.session_state.path[-1]) else ("●" if cell in st.session_state.visited else " "))
            kind = "primary" if (cell in st.session_state.visited) else "secondary"
            with cols[c]:
                if st.button(label, key=f"c_{r}_{c}", type=kind):
                    try_move(r, c); st.rerun()

    if st.session_state.completed and not st.session_state.score_saved:
        save_score(st.session_state.player_name, len(st.session_state.path), st.session_state.elapsed)
        st.session_state.score_saved = True
        st.balloons()

    if st.session_state.start_time and not st.session_state.completed:
        time.sleep(0.5); st.rerun()
