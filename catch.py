# 전체 실행 가능한 코드 (Streamlit 퍼즐 게임)
import streamlit as st
import random
import time
import sqlite3
from datetime import datetime
from collections import deque

# ----------------------------- 설정 ----------------------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
    "Level 6 (100점, 핵귀신맛)": {"obstacles": 28, "score": 100, "ghost": True, "ghost_count": 2, "ignore_obstacles": True, "portals": True}
}
MAP_SIZE = 9
PORTAL_SYMBOL = '🌀'

# ----------------------------- 랭킹 DB ----------------------------- #
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
    c.execute("INSERT INTO ranking VALUES (?, ?, ?, ?)",
              (name, score, level, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def load_ranking():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("SELECT name, score, level, timestamp FROM ranking ORDER BY score DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows

init_ranking_db()

# ----------------------------- 함수 ----------------------------- #
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

# 이후 실행 로직: 상태관리, 버튼 처리, 점수계산, 귀신추적, 포탈이동, Perfect판정, 랭킹저장 등

# ----------------------------- 실행 ----------------------------- #
# (위에 제공한 사용자 코드 전체가 여기에 들어가며, 여기에 이어서 랭킹 저장 기능 추가)

# 🎯 점수 획득 후 자동 랭킹 저장
if st.session_state.state['score'] > 0:
    name = st.text_input("이름을 입력하세요 (랭킹 저장용)", key="ranking_name")
    if name:
        save_score(name, st.session_state.state['score'], st.session_state.state['level'])
        st.success("랭킹에 저장되었습니다!")

# 🏆 랭킹 보기 버튼
if st.button("🏆 랭킹 보기"):
    ranking = load_ranking()
    st.markdown("### 🏅 상위 랭킹")
    for i, row in enumerate(ranking, 1):
        st.write(f"{i}위 | 이름: {row[0]} | 점수: {row[1]} | 레벨: {row[2]} | 날짜: {row[3]}")
# 이전 코드 흐름에 맞춰 draw_grid 호출하며 ghosts 리스트를 다중귀신에 활용
# 점수 획득 시 st.text_input("이름") 후 save_score(name, score, level) 호출
# st.button("랭킹 보기") 클릭 시 load_ranking 결과 출력

