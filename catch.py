import streamlit as st
import random
import time
import pandas as pd
from collections import deque

# ----------------------------- 설정 ----------------------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 5, "score": 5},
    "Level 2 (10점, 보통맛)": {"obstacles": 9, "score": 10},
    "Level 3 (20점, 매운맛)": {"obstacles": 13, "score": 20},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50},
}
MAP_SIZE = 8

# ----------------------------- 함수 ----------------------------- #
def generate_map(obstacle_count, goal_count=2):
    positions = [(i, j) for i in range(MAP_SIZE) for j in range(MAP_SIZE)]
    start = random.choice(positions)
    positions.remove(start)

    obstacles = set(random.sample(positions, obstacle_count))
    for ob in obstacles:
        positions.remove(ob)

    goals = random.sample(positions, goal_count)
    for goal in goals:
        positions.remove(goal)

    ghost1 = (max(0, start[0]-5), start[1])
    ghost2 = (min(MAP_SIZE-1, start[0]+3), start[1])
    return start, obstacles, goals, ghost1, ghost2

def rotate(direction, turn):
    idx = DIRECTIONS.index(direction)
    if turn == '오른쪽 회전': return DIRECTIONS[(idx + 1) % 4]
    else: return DIRECTIONS[(idx - 1) % 4]

def move_forward(pos, direction, steps):
    for _ in range(steps):
        offset = MOVE_OFFSET[direction]
        pos = (pos[0] + offset[0], pos[1] + offset[1])
        if not (0 <= pos[0] < MAP_SIZE and 0 <= pos[1] < MAP_SIZE):
            return None  # 벗어남
    return pos

def move_ghost(pos, player_pos, obstacles, ignore_obstacles=False):
    dx = player_pos[0] - pos[0]
    dy = player_pos[1] - pos[1]
    move_x = (1 if dx > 0 else -1) if dx != 0 else 0
    move_y = (1 if dy > 0 else -1) if dy != 0 else 0
    options = []
    if move_x: options.append((pos[0] + move_x, pos[1]))
    if move_y: options.append((pos[0], pos[1] + move_y))
    for opt in options:
        if 0 <= opt[0] < MAP_SIZE and 0 <= opt[1] < MAP_SIZE:
            if ignore_obstacles or opt not in obstacles:
                return opt
    return pos

def bfs_shortest_path(start, goals, obstacles):
    queue = deque([(start, [])])
    visited = set([start])
    while queue:
        current, path = queue.popleft()
        if current in goals:
            return path
        for move in MOVE_OFFSET.values():
            nx = current[0] + move[0]
            ny = current[1] + move[1]
            new = (nx, ny)
            if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE and new not in obstacles and new not in visited:
                visited.add(new)
                queue.append((new, path + [new]))
    return []

# ----------------------------- 초기화 ----------------------------- #
if 'level' not in st.session_state:
    st.session_state.level = list(LEVELS.keys())[0]
    st.session_state.start, st.session_state.obstacles, st.session_state.goals, st.session_state.ghost1, st.session_state.ghost2 = generate_map(LEVELS[st.session_state.level]['obstacles'])
    st.session_state.direction = 'UP'
    st.session_state.position = st.session_state.start
    st.session_state.commands = []
    st.session_state.score = 0
    st.session_state.total_score = 0
    st.session_state.high_score = 0
    st.session_state.result = ''
    st.session_state.ghost_path = []

# ----------------------------- 레벨 선택 ----------------------------- #
level = st.selectbox("레벨 선택", list(LEVELS.keys()))
if level != st.session_state.level:
    st.session_state.level = level
    st.session_state.start, st.session_state.obstacles, st.session_state.goals, st.session_state.ghost1, st.session_state.ghost2 = generate_map(LEVELS[level]['obstacles'])
    st.session_state.direction = 'UP'
    st.session_state.position = st.session_state.start
    st.session_state.commands = []
    st.session_state.result = ''
    st.session_state.ghost_path = []

# ----------------------------- UI ----------------------------- #
st.title("🤖 로봇 명령 퍼즐 게임")
st.markdown("명령어 예시: 앞으로, 앞으로 2, 앞으로 3, 왼쪽 회전, 오른쪽 회전, 집기")
commands = st.text_area("명령어 입력 (줄바꿈으로 분리)")

if st.button("실행"):
    pos = st.session_state.start
    direction = 'UP'
    ghost1 = st.session_state.ghost1
    ghost2 = st.session_state.ghost2
    ghost_path = []
    visited_goals = set()
    failed = False
    for cmd in commands.strip().split('\n'):
        cmd = cmd.strip()
        if cmd.startswith("앞으로"):
            parts = cmd.split()
            steps = int(parts[1]) if len(parts) > 1 else 1
            new_pos = move_forward(pos, direction, steps)
            if new_pos is None or any((pos[0] + i * MOVE_OFFSET[direction][0], pos[1] + i * MOVE_OFFSET[direction][1]) in st.session_state.obstacles for i in range(1, steps+1)):
                st.session_state.result = '장애물에 부딪혔습니다!'
                failed = True
                break
            pos = new_pos
        elif "회전" in cmd:
            direction = rotate(direction, cmd)
        elif cmd == "집기":
            if pos in st.session_state.goals:
                visited_goals.add(pos)
        # 귀신 이동
        ghost1 = move_ghost(ghost1, pos, st.session_state.obstacles, ignore_obstacles=("Level 5" in level))
        ghost2 = move_ghost(ghost2, pos, st.session_state.obstacles, ignore_obstacles=("Level 5" in level))
        ghost_path.append(ghost1)
        ghost_path.append(ghost2)
        if pos == ghost1 or pos == ghost2:
            st.session_state.result = '귀신에게 잡혔습니다!'
            failed = True
            break

    if not failed:
        st.session_state.score = len(visited_goals) * LEVELS[level]['score']
        st.session_state.total_score += st.session_state.score
        st.session_state.high_score = max(st.session_state.high_score, st.session_state.score)
        st.session_state.result = f"{len(visited_goals)}개 목표 도달! 🎉 점수: {st.session_state.score}"
        # Perfect 체크
        shortest = bfs_shortest_path(st.session_state.start, st.session_state.goals, st.session_state.obstacles)
        if len(shortest) + shortest.count('집기') == len(commands.strip().split('\n')) and len(visited_goals) == 2:
            st.session_state.result += "\n🌟 Perfect!"

    st.session_state.commands = commands.strip().split('\n')
    st.session_state.position = pos
    st.session_state.direction = direction
    st.session_state.ghost1 = ghost1
    st.session_state.ghost2 = ghost2
    st.session_state.ghost_path = ghost_path

# ----------------------------- 출력 ----------------------------- #
st.markdown(f"**현재 점수:** {st.session_state.score} / **최고 점수:** {st.session_state.high_score} / **누적 점수:** {st.session_state.total_score}")
st.markdown(f"**결과:** {st.session_state.result}")

# ----------------------------- 맵 출력 ----------------------------- #
grid = ""
for i in range(MAP_SIZE):
    for j in range(MAP_SIZE):
        cell = '⬜'
        if (i, j) == st.session_state.position:
            cell = '🤡' + DIRECTION_SYMBOLS[st.session_state.direction]  # 광대 + 방향 표시
        elif (i, j) in st.session_state.obstacles:
            cell = '⬛'
        elif (i, j) in st.session_state.goals:
            cell = '🎯'
        elif (i, j) == st.session_state.ghost1:
            cell = '👻'
        elif (i, j) == st.session_state.ghost2:
            cell = '💀'
        elif (i, j) in st.session_state.ghost_path:
            cell = '·'
        grid += cell
    grid += '\n'
st.text(grid)

if st.button("다시 시작"):
    st.session_state.start, st.session_state.obstacles, st.session_state.goals, st.session_state.ghost1, st.session_state.ghost2 = generate_map(LEVELS[st.session_state.level]['obstacles'])
    st.session_state.direction = 'UP'
    st.session_state.position = st.session_state.start
    st.session_state.commands = []
    st.session_state.score = 0
    st.session_state.result = ''
    st.session_state.ghost_path = []
