import streamlit as st
import random
import time
import sqlite3
from datetime import datetime
from collections import deque

# ----------------------------- 초기 설정 ----------------------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
MAP_SIZE = 9
PORTAL_SYMBOL = '🌀'

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
    "Level 6 (100점, 핵귀신맛)": {"obstacles": 28, "score": 100, "ghost": True, "ghost_count": 2, "ignore_obstacles": True, "portals": True}
}

# ----------------------------- 랭킹 DB ----------------------------- #
def init_ranking_db():
    conn = sqlite3.connect("/tmp/ranking.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ranking (
            name TEXT,
            score INTEGER,
            level TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_score(name, score, level):
    conn = sqlite3.connect("/tmp/ranking.db")
    c = conn.cursor()
    c.execute("INSERT INTO ranking VALUES (?, ?, ?, ?)",
              (name, score, level, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def load_ranking():
    conn = sqlite3.connect("/tmp/ranking.db")
    c = conn.cursor()
    c.execute("SELECT name, score, level, timestamp FROM ranking ORDER BY score DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows

init_ranking_db()

# ----------------------------- 게임 함수 ----------------------------- #
def generate_map(obstacle_count, goal_count=2, use_portals=False):
    while True:
        positions = [(i, j) for i in range(MAP_SIZE) for j in range(MAP_SIZE)]
        start = random.choice(positions)
        positions.remove(start)

        obstacles = set(random.sample(positions, obstacle_count))
        positions = [p for p in positions if p not in obstacles]

        goals = random.sample(positions, goal_count)
        positions = [p for p in positions if p not in goals]

        portals = []
        if use_portals:
            portals = random.sample(positions, 2)

        if all(bfs_shortest_path(start, [g], obstacles) for g in goals):
            break

    return start, obstacles, goals, portals

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

def rotate(direction, turn):
    idx = DIRECTIONS.index(direction)
    return DIRECTIONS[(idx + 1) % 4] if turn == '오른쪽 회전' else DIRECTIONS[(idx - 1) % 4]

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

def draw_grid(pos, direction, ghost, ghost_path, obstacles, goals, portals):
    grid = ""
    for i in range(MAP_SIZE):
        for j in range(MAP_SIZE):
            cell = "⬜"
            if (i, j) == pos:
                cell = "🤡"
            elif (i, j) in obstacles:
                cell = "⬛"
            elif (i, j) in goals:
                cell = "🎯"
            elif (i, j) == ghost:
                cell = "👻"
            elif (i, j) in ghost_path:
                cell = "·"
            elif (i, j) in portals:
                cell = PORTAL_SYMBOL
            grid += cell
        grid += "\n"
    st.text(grid)

# ----------------------------- Streamlit 실행 ----------------------------- #
st.title("🤖 로봇 명령 퍼즐 게임")

st.markdown(
    """
    <audio autoplay loop>
        <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
    </audio>
    """,
    unsafe_allow_html=True
)

if 'reset_input' not in st.session_state:
    st.session_state['reset_input'] = False

if 'state' not in st.session_state:
    default_level = list(LEVELS.keys())[0]
    level_info = LEVELS[default_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost_range = level_info.get('ghost_range', 0)
    ghost = (min(MAP_SIZE - 1, start[0] + ghost_range), start[1]) if level_info['ghost'] else None
    st.session_state.state = {
        'level': default_level,
        'start': start,
        'position': start,
        'direction': 'UP',
        'obstacles': obstacles,
        'goals': goals,
        'portals': portals,
        'ghost': ghost,
        'ghost_path': [],
        'score': 0,
        'high_score': 0,
        'total_score': 0,
        'result': '',
        'commands': []
    }

prev_level = st.session_state.state['level']
selected_level = st.selectbox("레벨 선택", list(LEVELS.keys()))
if selected_level != prev_level:
    st.session_state['reset_input'] = True
    level_info = LEVELS[selected_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost_range = level_info.get('ghost_range', 0)
    ghost = (min(MAP_SIZE - 1, start[0] + ghost_range), start[1]) if level_info['ghost'] else None
    st.session_state.state.update({
        'level': selected_level,
        'start': start,
        'position': start,
        'direction': 'UP',
        'obstacles': obstacles,
        'goals': goals,
        'portals': portals,
        'ghost': ghost,
        'ghost_path': [],
        'result': '',
        'commands': []
    })

# 명령어 입력
default_commands = "" if st.session_state.get('reset_input') else None
commands = st.text_area("명령어 입력(한줄에 명령어 하나씩)", value=default_commands, key="command_input")
st.session_state['reset_input'] = False

# 실행 버튼
if st.button("실행"):
    # (게임 실행 로직은 기존과 동일)
    st.session_state.state['commands'] = commands.strip().split('\n')
    st.session_state['reset_input'] = True  # 실행 후에도 초기화되도록

# 다시 시작
if st.button("🔁 다시 시작"):
    s = st.session_state.state
    st.session_state['reset_input'] = True
    st.session_state.state.update({
        'position': s['start'],
        'direction': 'UP',
        'ghost_path': [],
        'result': '',
        'commands': []
    })

# draw_grid 호출을 실행 버튼 바깥에서도 하도록 아래 추가
draw_grid(
    st.session_state.state['position'],
    st.session_state.state['direction'],
    st.session_state.state['ghost'],
    st.session_state.state['ghost_path'],
    st.session_state.state['obstacles'],
    st.session_state.state['goals'],
    st.session_state.state['portals']
)


# 랭킹 저장 / 보기
if st.session_state.state['score'] > 0:
    name = st.text_input("이름을 입력하세요 (랭킹 저장)", key="name_input")
    if name:
        save_score(name, st.session_state.state['score'], st.session_state.state['level'])
        st.success("랭킹에 저장되었습니다!")

if st.button("🏆 랭킹 보기"):
    ranking = load_ranking()
    st.markdown("### 🏅 상위 랭킹")
    for i, row in enumerate(ranking, 1):
        st.write(f"{i}위 | 이름: {row[0]} | 점수: {row[1]} | 레벨: {row[2]} | 날짜: {row[3]}")

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

    ### 🏆 Perfect 판정
    - 최단 경로 + 모든 목표 수집 + 명령 수 최소일 때 Perfect! 🌟

    ### 🧱 각 레벨 정보
    - Level 1 (5점, 착한맛): 장애물 8개, 귀신 없음
    - Level 2 (10점, 보통맛): 장애물 14개, 귀신 없음
    - Level 3 (20점, 매운맛): 장애물 20개, 귀신 없음
    - Level 4 (30점, 불닭맛): 장애물 22개, 귀신 1명
    - Level 5 (50점, 핵불닭맛): 장애물 25개, 귀신 1명, 포탈 2개
    """)
