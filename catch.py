import streamlit as st
import random
import time
import sqlite3
from datetime import datetime
from collections import deque

# ---------------- 설정 ---------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
PORTAL_SYMBOL = '🌀'
MAP_SIZE = 9

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
    "Level 6 (100점, 미친맛)": {"obstacles": 30, "score": 100, "ghost": True, "ghost_range": 1, "ignore_obstacles": True, "portals": True, "ghost_count": 2},
}

# ---------------- DB 초기화 ---------------- #
def init_ranking_db():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ranking (
            name TEXT,
            score INTEGER,
            level TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_score(name, score, level):
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("INSERT INTO ranking VALUES (?, ?, ?, ?)", (name, score, level, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    def load_ranking():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("SELECT name, score, level, timestamp FROM ranking ORDER BY score DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows

def generate_map(obstacle_count, goal_count=2, use_portals=False):
    while True:
        positions = [(i, j) for i in range(MAP_SIZE) for j in range(MAP_SIZE)]
        start = random.choice(positions)
        positions.remove(start)
        obstacles = set(random.sample(positions, obstacle_count))
        positions = [p for p in positions if p not in obstacles]
        goals = random.sample(positions, goal_count)
        positions = [p for p in positions if p not in goals]
        portals = random.sample(positions, 2) if use_portals else []
        if all(bfs_shortest_path(start, [g], obstacles) for g in goals):
            return start, obstacles, goals, portals

def rotate(direction, turn):
    idx = DIRECTIONS.index(direction)
    return DIRECTIONS[(idx + 1) % 4] if "오른쪽" in turn else DIRECTIONS[(idx - 1) % 4]

def move_forward(pos, direction, steps):
    for _ in range(steps):
        offset = MOVE_OFFSET[direction]
        pos = (pos[0] + offset[0], pos[1] + offset[1])
        if not (0 <= pos[0] < MAP_SIZE and 0 <= pos[1] < MAP_SIZE):
            return None
    return pos

def move_ghost(pos, target, obstacles, ignore_obstacles=False):
    dx, dy = target[0] - pos[0], target[1] - pos[1]
    options = []
    if dx != 0:
        options.append((pos[0] + (1 if dx > 0 else -1), pos[1]))
    if dy != 0:
        options.append((pos[0], pos[1] + (1 if dy > 0 else -1)))
    for opt in options:
        if 0 <= opt[0] < MAP_SIZE and 0 <= opt[1] < MAP_SIZE:
            if ignore_obstacles or opt not in obstacles:
                return opt
    return pos
def bfs_shortest_path(start, goals, obstacles):
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        if current in goals:
            return path
        for d in MOVE_OFFSET.values():
            nx, ny = current[0] + d[0], current[1] + d[1]
            next_pos = (nx, ny)
            if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE and next_pos not in obstacles and next_pos not in visited:
                visited.add(next_pos)
                queue.append((next_pos, path + [next_pos]))
    return []

def draw_grid(position, direction, ghosts, ghost_path, obstacles, goals, portals):
    grid = ""
    for i in range(MAP_SIZE):
        for j in range(MAP_SIZE):
            cell = '⬜'
            if (i, j) == position:
                cell = '🤡'
            elif (i, j) in obstacles:
                cell = '⬛'
            elif (i, j) in goals:
                cell = '🎯'
            elif (i, j) in ghosts:
                cell = '👻'
            elif (i, j) in ghost_path:
                cell = '·'
            elif (i, j) in portals:
                cell = PORTAL_SYMBOL
            grid += cell
        grid += '\n'
    st.text(grid)

# ---------------- 상태 초기화 ---------------- #
def reset_state(selected_level):
    info = LEVELS[selected_level]
    start, obstacles, goals, portals = generate_map(info["obstacles"], use_portals=info.get("portals", False))
    ghost_range = info.get("ghost_range", 0)
    ghosts = []
    if info.get("ghost"):
        ghosts.append((min(MAP_SIZE - 1, start[0] + ghost_range), start[1]))
        if selected_level == "Level 6 (100점, 극한맛)":
            ghosts.append((max(0, start[0] - ghost_range), start[1]))
    return {
        "level": selected_level,
        "start": start,
        "obstacles": obstacles,
        "goals": goals,
        "portals": portals,
        "position": start,
        "direction": "UP",
        "ghosts": ghosts,
        "ghost_path": [],
        "score": 0,
        "high_score": 0,
        "total_score": 0,
        "result": "",
    }
# ---------------- Streamlit 시작 ---------------- #
init_ranking_db()
st.title("🤖 로봇 명령 퍼즐 게임")
st.markdown(
    """<audio autoplay loop>
    <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
    </audio>""",
    unsafe_allow_html=True
)

if "state" not in st.session_state:
    selected_level = list(LEVELS.keys())[0]
    st.session_state.state = reset_state(selected_level)
    st.session_state.commands_input = ""

# ---------------- 레벨 선택 ---------------- #
selected_level = st.selectbox("레벨 선택", list(LEVELS.keys()), index=list(LEVELS.keys()).index(st.session_state.state["level"]))
if selected_level != st.session_state.state["level"]:
    st.session_state.state = reset_state(selected_level)
    st.session_state.commands_input = ""

# ---------------- 명령어 입력 ---------------- #
commands = st.text_area("명령어 입력", value=st.session_state.commands_input, key="command_area")
if st.button("실행"):
    s = st.session_state.state
    pos = s["position"]
    direction = s["direction"]
    ghosts = s["ghosts"]
    ghost_path = []
    goals_reached = set()
    failed = False

    for line in commands.strip().split('\n'):
        if line.startswith("앞으로"):
            step = int(line.split()[1]) if len(line.split()) > 1 else 1
            for _ in range(step):
                next_pos = move_forward(pos, direction, 1)
                if next_pos is None or next_pos in s["obstacles"]:
                    s["result"] = "❌ 충돌 또는 벽!"
                    failed = True
                    break
                pos = next_pos
        elif "회전" in line:
            direction = rotate(direction, line)
        elif line == "집기" and pos in s["goals"]:
            goals_reached.add(pos)
        if failed:
            break
        new_ghosts = []
        for ghost in ghosts:
            moved = move_ghost(ghost, pos, s["obstacles"], LEVELS[s["level"]].get("ignore_obstacles", False))
            if moved == pos:
                s["result"] = "👻 귀신에게 잡힘!"
                failed = True
            new_ghosts.append(moved)
            ghost_path.append(moved)
        ghosts = new_ghosts
        draw_grid(pos, direction, ghosts, ghost_path, s["obstacles"], s["goals"], s["portals"])
        time.sleep(0.15)

    if not failed:
        score = len(goals_reached) * LEVELS[s["level"]]["score"]
        s["score"] = score
        s["total_score"] += score
        s["high_score"] = max(s["high_score"], score)
        s["result"] = f"🎯 목표 도달: {len(goals_reached)}, 점수: {score}"
        shortest = bfs_shortest_path(s["start"], s["goals"], s["obstacles"])
        if len(commands.strip().split('\n')) == len(shortest) + 2 and len(goals_reached) == 2:
            s["result"] += "\n🌟 Perfect!"

    s.update({"position": pos, "direction": direction, "ghosts": ghosts, "ghost_path": ghost_path})
    st.session_state.commands_input = ""
# ---------------- 결과 출력 ---------------- #
s = st.session_state.state
st.markdown(f"**현재 점수:** {s['score']} / **최고 점수:** {s['high_score']} / **누적 점수:** {s['total_score']}")
st.markdown(f"**결과:** {s['result']}")
draw_grid(s["position"], s["direction"], s["ghosts"], s["ghost_path"], s["obstacles"], s["goals"], s["portals"])

# ---------------- 다시 시작 ---------------- #
if st.button("🔁 다시 시작"):
    st.session_state.state = reset_state(st.session_state.state["level"])
    st.session_state.commands_input = ""

# ---------------- 랭킹 등록 ---------------- #
if s["score"] > 0:
    name = st.text_input("랭킹 등록할 이름 입력")
    if name:
        save_score(name, s["score"], s["level"])
        st.success("✅ 랭킹에 등록 완료!")

if st.button("🏆 랭킹 보기", key="ranking_btn"):
    for i, (n, sc, lv, ts) in enumerate(load_ranking(), 1):
        st.write(f"{i}위 | 이름: {n} | 점수: {sc} | 레벨: {lv} | 날짜: {ts}")

# ---------------- 게임 설명 ---------------- #
with st.expander("📘 게임 설명 보기"):
    st.markdown("""
    ### 🎮 게임 방법
    로봇 🤡에게 명령어를 입력하여 두 개의 🎯 목표 지점을 방문하고 집기 명령으로 수집하세요!  
    장애물(⬛)을 피하고, 귀신(👻)에게 잡히지 않도록 조심하세요!

    ### ✏️ 사용 가능한 명령어
    - 앞으로 : 한 칸 전진
    - 앞으로 2, 앞으로 3 : 여러 칸 전진
    - 왼쪽 회전 : 반시계 방향으로 90도 회전
    - 오른쪽 회전 : 시계 방향으로 90도 회전
    - 집기 : 현재 칸에 목표물이 있을 경우 수집

    ### 🌀 포탈 (Level 5 이상)
    - 포탈(🌀)에 들어가면 다른 포탈로 순간 이동!
    - 귀신은 포탈을 사용할 수 없습니다.

    ### 👻 귀신
    - Level 4: 귀신 1마리 (장애물 피해 추적)
    - Level 5: 귀신 1마리 (장애물 무시)
    - Level 6: 귀신 2마리 (장애물 무시)

    ### 🏆 Perfect 조건
    - 최단 경로 이동 + 명령어 수 최소 + 목표 모두 수집 시 Perfect! 🌟

    ### 🧱 레벨 구성
    - Level 1 (5점, 착한맛): 장애물 8개, 귀신 없음
    - Level 2 (10점, 보통맛): 장애물 14개, 귀신 없음
    - Level 3 (20점, 매운맛): 장애물 20개, 귀신 없음
    - Level 4 (30점, 불닭맛): 장애물 22개, 귀신 1명
    - Level 5 (50점, 핵불닭맛):

