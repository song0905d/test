import streamlit as st
import random
import time
import sqlite3
from collections import deque

# 설정
GRID_SIZE = 9
PLAYER_ICON = "🤡"
GOAL_ICON = "🎯"
OBSTACLE_ICON = "⬛"
GHOST_ICON = ["👻", "💀"]
PORTAL_ICON = "🌀"

DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_block": True, "ghost_range": 7},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_block": False, "ghost_range": 5, "portal": 2},
    "Level 6 (100점, 지옥맛)": {"obstacles": 28, "score": 100, "ghost": True, "ghost_block": False, "ghost_range": 1, "ghost_spawn_surround": 2, "portal": 2},
}

# DB 초기화
def init_ranking_db():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS ranking (
        name TEXT,
        score INTEGER
    )""")
    conn.commit()
    conn.close()

def save_score(name, score):
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("INSERT INTO ranking VALUES (?, ?)", (name, score))
    conn.commit()
    conn.close()

def get_ranking():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("SELECT name, score FROM ranking ORDER BY score DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows

# 세션 초기화
if "level" not in st.session_state:
    st.session_state.level = list(LEVELS.keys())[0]

if "grid" not in st.session_state:
    st.session_state.grid = None

if "commands_input" not in st.session_state:
    st.session_state.commands_input = ""

if "score" not in st.session_state:
    st.session_state.score = 0
if "high_score" not in st.session_state:
    st.session_state.high_score = 0

# 맵 생성
def generate_map(level_key):
    grid = [["" for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    player_pos = (0, 0)
    grid[0][0] = "P"
    goal_pos = [(GRID_SIZE - 1, GRID_SIZE - 1)]
    grid[GRID_SIZE - 1][GRID_SIZE - 1] = "G"
    data = LEVELS[level_key]
    ghost_pos = []
    portal_pos = []

    for _ in range(data.get("obstacles", 0)):
        while True:
            r, c = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
            if grid[r][c] == "":
                grid[r][c] = "X"
                break

    if data.get("portal", 0) == 2:
        for _ in range(2):
            while True:
                r, c = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
                if grid[r][c] == "":
                    grid[r][c] = "O"
                    portal_pos.append((r, c))
                    break

    if data.get("ghost"):
        if "ghost_spawn_surround" in data:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                gr, gc = player_pos[0] + dr, player_pos[1] + dc
                if 0 <= gr < GRID_SIZE and 0 <= gc < GRID_SIZE and grid[gr][gc] == "":
                    grid[gr][gc] = "ghost"
                    ghost_pos.append((gr, gc))
                    if len(ghost_pos) >= data["ghost_spawn_surround"]:
                        break
        else:
            gr, gc = GRID_SIZE - data["ghost_range"], GRID_SIZE - data["ghost_range"]
            if grid[gr][gc] == "":
                grid[gr][gc] = "ghost"
                ghost_pos.append((gr, gc))

    return grid, player_pos, goal_pos, ghost_pos, portal_pos

# UI 출력
def print_map(grid, player_pos, ghost_pos, goal_pos, portal_pos, direction):
    symbol_grid = [["⬜" for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == "X":
                symbol_grid[r][c] = OBSTACLE_ICON
            elif grid[r][c] == "O":
                symbol_grid[r][c] = PORTAL_ICON
            elif (r, c) in goal_pos:
                symbol_grid[r][c] = GOAL_ICON
            elif grid[r][c] == "ghost":
                symbol_grid[r][c] = random.choice(GHOST_ICON)
    for idx, (gr, gc) in enumerate(ghost_pos):
        symbol_grid[gr][gc] = GHOST_ICON[idx % 2]
    r, c = player_pos
    symbol_grid[r][c] = PLAYER_ICON + DIRECTION_SYMBOLS[direction]
    st.markdown("### 🧭 게임 맵")
    for row in symbol_grid:
        st.markdown("".join(row))

# 게임 로직
def run_game(commands, grid, player_pos, ghost_pos, goal_pos, portal_pos, level_data):
    direction = "RIGHT"
    score = 0
    perfect = True

    for cmd in commands:
        cmd = cmd.strip()
        if " " in cmd:
            base, count = cmd.split()
            count = int(count)
        else:
            base, count = cmd, 1

        if base == "왼쪽":
            direction = DIRECTIONS[(DIRECTIONS.index(direction) - count) % 4]
        elif base == "오른쪽":
            direction = DIRECTIONS[(DIRECTIONS.index(direction) + count) % 4]
        elif base == "앞으로":
            for _ in range(count):
                dr, dc = MOVE_OFFSET[direction]
                nr, nc = player_pos[0] + dr, player_pos[1] + dc
                if not (0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE):
                    perfect = False
                    break
                if grid[nr][nc] == "X":
                    perfect = False
                    break
                if grid[nr][nc] == "ghost":
                    st.error("👻 귀신에게 잡혔습니다!")
                    return score, False
                if grid[nr][nc] == "O" and len(portal_pos) == 2:
                    nr, nc = portal_pos[1] if (nr, nc) == portal_pos[0] else portal_pos[0]
                player_pos = (nr, nc)

                new_ghosts = []
                for gr, gc in ghost_pos:
                    path = bfs((gr, gc), player_pos, grid if level_data.get("ghost_block") else None)
                    if len(path) > 1:
                        new_ghosts.append(path[1])
                        if path[1] == player_pos:
                            st.error("👻 귀신에게 잡혔습니다!")
                            return score, False
                    else:
                        new_ghosts.append((gr, gc))
                ghost_pos = new_ghosts

        print_map(grid, player_pos, ghost_pos, goal_pos, portal_pos, direction)
        time.sleep(0.5)

    reached_goals = sum([1 for g in goal_pos if player_pos == g])
    score = level_data["score"] * reached_goals
    if reached_goals >= len(goal_pos):
        st.success("🎉 목표에 도달했습니다!")
        if perfect:
            st.balloons()
            st.markdown("✅ **Perfect!**")
    else:
        st.warning("목표에 도달하지 못했습니다.")
    return score, True

# BFS 경로 탐색
def bfs(start, goal, grid):
    q = deque([(start, [])])
    visited = set()
    while q:
        (r, c), path = q.popleft()
        if (r, c) == goal:
            return path + [(r, c)]
        for dr, dc in MOVE_OFFSET.values():
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE and (nr, nc) not in visited:
                if grid and grid[nr][nc] == "X":
                    continue
                visited.add((nr, nc))
                q.append(((nr, nc), path + [(r, c)]))
    return []

# 앱 실행
def main():
    st.title("🤖 로봇 명령 퍼즐 게임")

    init_ranking_db()

    st.markdown("### 🎮 레벨 선택")
    level_key = st.selectbox("난이도를 선택하세요", list(LEVELS.keys()), index=list(LEVELS.keys()).index(st.session_state.level))
    level_data = LEVELS[level_key]

    if st.button("🔁 다시 시작"):
        st.session_state.level = level_key
        st.session_state.grid, st.session_state.player_pos, st.session_state.goal_pos, st.session_state.ghost_pos, st.session_state.portal_pos = generate_map(level_key)
        st.session_state.commands_input = ""

    if st.session_state.grid is None or st.session_state.level != level_key:
        st.session_state.level = level_key
        st.session_state.grid, st.session_state.player_pos, st.session_state.goal_pos, st.session_state.ghost_pos, st.session_state.portal_pos = generate_map(level_key)
        st.session_state.commands_input = ""

    st.markdown(f"**현재 점수:** {st.session_state.score} / **최고 점수:** {st.session_state.high_score}")
    print_map(st.session_state.grid, st.session_state.player_pos, st.session_state.ghost_pos, st.session_state.goal_pos, st.session_state.portal_pos, "RIGHT")

    st.markdown("### 📝 명령어 입력")
    st.session_state.commands_input = st.text_area("명령어를 입력하세요", value=st.session_state.commands_input, height=100, key="cmd_input")

    if st.button("🚀 실행"):
        commands = [line.strip() for line in st.session_state.commands_input.split("\n") if line.strip()]
        score, alive = run_game(commands, st.session_state.grid, st.session_state.player_pos, st.session_state.ghost_pos, st.session_state.goal_pos, st.session_state.portal_pos, level_data)
        if alive:
            st.session_state.score = score
            if score > st.session_state.high_score:
                st.session_state.high_score = score

    if st.button("📋 랭킹 저장"):
        name = st.text_input("이름을 입력하세요", key="rank_name")
        if name:
            save_score(name, st.session_state.score)
            st.success("랭킹 저장 완료!")

    if st.button("🏆 랭킹 보기"):
        st.markdown("### 🏆 상위 랭킹")
        ranking = get_ranking()
        for i, (name, score) in enumerate(ranking, 1):
            st.markdown(f"**{i}. {name} - {score}점**")

main()

# ------------------ 배경음악 자동 재생 ------------------
import base64

def autoplay_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
        <audio autoplay loop>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        st.markdown(md, unsafe_allow_html=True)

autoplay_audio("bgm.mp3")  # mp3 파일명에 맞게 조정
# -------------------------------------------------------
