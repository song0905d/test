import streamlit as st
import random
import time
import sqlite3
from datetime import datetime
from collections import deque

DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
MAP_SIZE = 9
PORTAL_SYMBOL = '🌀'

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
    "Level 6 (100점, 지옥맛)": {"obstacles": 30, "score": 100, "ghost": True, "ghost_range": 1, "ignore_obstacles": True, "portals": True, "ghost_count": 2},
}

def init_db():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ranking (
        name TEXT, score INTEGER, level TEXT, timestamp TEXT)''')
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
    result = c.fetchall()
    conn.close()
    return result

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
            next_pos = (current[0] + d[0], current[1] + d[1])
            if 0 <= next_pos[0] < MAP_SIZE and 0 <= next_pos[1] < MAP_SIZE and next_pos not in visited and next_pos not in obstacles:
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
            elif (i, j) in portals:
                cell = PORTAL_SYMBOL
            elif (i, j) in ghosts:
                cell = '👻'
            elif (i, j) in ghost_path:
                cell = '·'
            grid += cell
        grid += '\n'
    st.text(grid)

# ---------------------- 게임 로직 ---------------------- #

init_db()
st.title("🤖 로봇 명령 퍼즐 게임")

if "state" not in st.session_state:
    default = list(LEVELS.keys())[0]
    info = LEVELS[default]
    start, obstacles, goals, portals = generate_map(info["obstacles"], use_portals=info.get("portals", False))
    ghosts = []
    for i in range(info.get("ghost_count", 1 if info.get("ghost") else 0)):
        ghost_pos = (max(0, min(MAP_SIZE - 1, start[0] + info.get("ghost_range", 0))), start[1] + i)
        ghosts.append(ghost_pos)
    st.session_state.state = {
        "level": default,
        "start": start,
        "position": start,
        "direction": "UP",
        "obstacles": obstacles,
        "goals": goals,
        "portals": portals,
        "ghosts": ghosts,
        "ghost_path": [],
        "score": 0,
        "result": "",
    }

state = st.session_state.state
selected_level = st.selectbox("레벨 선택", list(LEVELS.keys()))
if selected_level != state["level"]:
    info = LEVELS[selected_level]
    start, obstacles, goals, portals = generate_map(info["obstacles"], use_portals=info.get("portals", False))
    ghosts = []
    for i in range(info.get("ghost_count", 1 if info.get("ghost") else 0)):
        ghost_pos = (max(0, min(MAP_SIZE - 1, start[0] + info.get("ghost_range", 0))), start[1] + i)
        ghosts.append(ghost_pos)
    st.session_state.state = {
        "level": selected_level,
        "start": start,
        "position": start,
        "direction": "UP",
        "obstacles": obstacles,
        "goals": goals,
        "portals": portals,
        "ghosts": ghosts,
        "ghost_path": [],
        "score": 0,
        "result": "",
    }

commands = st.text_area("명령어 입력", value="", key="cmd_input")
if st.button("실행"):
    s = st.session_state.state
    pos, direction = s["position"], s["direction"]
    ghosts = s["ghosts"]
    ghost_path = []
    result = ""
    goals_reached = set()
    failed = False
    for line in commands.strip().split("\n"):
        if line.startswith("앞으로"):
            steps = int(line.split()[1]) if len(line.split()) > 1 else 1
            for _ in range(steps):
                next_pos = move_forward(pos, direction, 1)
                if next_pos is None or next_pos in s["obstacles"]:
                    result = "❌ 충돌!"
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
        for g in ghosts:
            ng = move_ghost(g, pos, s["obstacles"], LEVELS[s["level"]].get("ignore_obstacles", False))
            if ng == pos:
                result = "👻 귀신에게 잡힘!"
                failed = True
                break
            new_ghosts.append(ng)
            ghost_path.append(ng)
        ghosts = new_ghosts
        draw_grid(pos, direction, ghosts, ghost_path, s["obstacles"], s["goals"], s["portals"])
        time.sleep(0.2)

    if not failed:
        score = len(goals_reached) * LEVELS[s["level"]]["score"]
        result = f"🎯 목표 도달: {len(goals_reached)}개, 점수: {score}"
        path = bfs_shortest_path(s["start"], s["goals"], s["obstacles"])
        if len(goals_reached) == 2 and len(commands.strip().split('\n')) <= len(path) + 2:
            result += " 🌟 Perfect!"
        s["score"] = score

    s.update({"position": pos, "direction": direction, "ghosts": ghosts, "ghost_path": ghost_path, "result": result})

if st.button("🔁 다시 시작"):
    s = st.session_state.state
    s.update({
        "position": s["start"],
        "direction": "UP",
        "ghosts": s["ghosts"],
        "ghost_path": [],
        "score": 0,
        "result": ""
    })
    st.session_state["cmd_input"] = ""

s = st.session_state.state
draw_grid(s["position"], s["direction"], s["ghosts"], s["ghost_path"], s["obstacles"], s["goals"], s["portals"])
st.markdown(f"**현재 점수:** {s['score']} | **결과:** {s['result']}")

if s["score"] > 0:
    name = st.text_input("랭킹 등록 이름")
    if name:
        save_score(name, s["score"], s["level"])
        st.success("✅ 등록 완료!")

if st.button("🏆 랭킹 보기"):
    for i, row in enumerate(load_ranking(), 1):
        st.write(f"{i}위 | 이름: {row[0]} | 점수: {row[1]} | 레벨: {row[2]} | 시간: {row[3]}")



# 설명
with st.expander("📘 게임 설명 보기"):
    st.markdown("""
    ### 🎮 게임 방법
    로봇 🤡에게 명령어를 입력하여 두 개의 🎯 목표 지점을 방문하고 집기 명령으로 수집하세요!  
    장애물(⬛)을 피하고, 귀신(👻)에게 잡히지 않도록 조심하세요!

    ### ✏️ 사용 가능한 명령어 (기본 방향 위)
    - 앞으로 : 한 칸 전진
    - 앞으로 2, 앞으로 3 : 여러 칸 전진
    - 왼쪽 회전 : 반시계 방향으로 90도 회전
    - 오른쪽 회전 : 시계 방향으로 90도 회전
    - 집기 : 현재 칸에 목표물이 있을 경우 수집

    ### 🌀 포탈 (Level 5)
    - 포탈(🌀)에 들어가면 다른 포탈 근처 랜덤 위치로 순간 이동!
    - 귀신은 포탈을 사용할 수 없습니다.

    ### 👻 귀신
    - 레벨 4: 귀신은 장애물을 피해서 이동
    - 레벨 5: 귀신은 장애물을 무시하고 직진 추적
    - 레벨 6: 레벨 5의 귀신이 2마리 등장 (오류 있음)

    ### 🏆 Perfect 판정
    - 최단 경로 + 모든 목표 수집 + 명령 수 최소일 때 Perfect! 🌟

    ### 🧱 각 레벨 정보
    - Level 1 (5점, 착한맛): 장애물 8개, 귀신 없음
    - Level 2 (10점, 보통맛): 장애물 14개, 귀신 없음
    - Level 3 (20점, 매운맛): 장애물 20개, 귀신 없음
    - Level 4 (30점, 불닭맛): 장애물 22개, 귀신 1명
    - Level 5 (50점, 핵불닭맛): 장애물 25개, 귀신 1명, 포탈 2개
    - Level 6 (100점, 맛): 장애물 30개, 귀신 2명, 포탈 2개
    """)
