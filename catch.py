from textwrap import dedent

full_code = dedent("""
import streamlit as st
import random
import sqlite3

# -------------------- 초기 설정 -------------------- #
GRID_SIZE = 9
DIRECTIONS = {'앞으로': (-1, 0), '뒤로': (1, 0), '왼쪽': (0, -1), '오른쪽': (0, 1)}
DIRECTION_SYMBOLS = {'앞으로': '↑', '뒤로': '↓', '왼쪽': '←', '오른쪽': '→'}

LEVELS = {
    "Level 1 (5점, 착한맛)": {"score": 5, "obstacles": 8, "ghost": False},
    "Level 2 (10점, 보통맛)": {"score": 10, "obstacles": 14, "ghost": False},
    "Level 3 (20점, 매운맛)": {"score": 20, "obstacles": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"score": 30, "obstacles": 22, "ghost": True, "ghost_count": 1, "ghost_blocked": True, "ghost_nearby": False},
    "Level 5 (50점, 핵불닭맛)": {"score": 50, "obstacles": 25, "ghost": True, "ghost_count": 1, "ghost_blocked": False, "ghost_nearby": False},
    "Level 6 (100점, 헬맛)": {"score": 100, "obstacles": 28, "ghost": True, "ghost_count": 2, "ghost_blocked": False, "ghost_nearby": True}
}

# -------------------- DB 초기화 -------------------- #
def init_ranking_db():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ranking (name TEXT, score INTEGER)''')
    conn.commit()
    conn.close()

def save_score(name, score):
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("INSERT INTO ranking (name, score) VALUES (?, ?)", (name, score))
    conn.commit()
    conn.close()

def get_rankings():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute("SELECT name, score FROM ranking ORDER BY score DESC LIMIT 10")
    rankings = c.fetchall()
    conn.close()
    return rankings

# -------------------- 맵 생성 함수 -------------------- #
def generate_map(level_config):
    grid = [["⬜" for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    player_pos = [GRID_SIZE - 1, 0]
    targets = [[0, GRID_SIZE - 1], [0, GRID_SIZE // 2]]
    obstacles = set()
    portals = []
    ghost_pos = []

    while len(obstacles) < level_config["obstacles"]:
        r, c = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
        if [r, c] not in targets and [r, c] != player_pos:
            obstacles.add((r, c))

    for r, c in obstacles:
        grid[r][c] = "⬛"

    for tr in targets:
        grid[tr[0]][tr[1]] = "🏁"

    portal_pairs = [[[1, 1], [7, 7]]]
    for p1, p2 in portal_pairs:
        grid[p1[0]][p1[1]] = "🌀"
        grid[p2[0]][p2[1]] = "🌀"
        portals.append((tuple(p1), tuple(p2)))

    if level_config.get("ghost"):
        start = player_pos
        for i in range(level_config["ghost_count"]):
            if level_config.get("ghost_nearby"):
                offset = [(0,1), (1,0), (-1,0), (0,-1)]
                gx, gy = start[0] + offset[i][0], start[1] + offset[i][1]
            else:
                gx, gy = start[0] - (5 + i), start[1]
            if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                ghost_pos.append([gx, gy])

    return grid, player_pos, targets, portals, list(obstacles), ghost_pos

# -------------------- 출력 함수 -------------------- #
def render(grid, player_pos, ghost_pos, direction):
    temp = [row.copy() for row in grid]
    for g in ghost_pos:
        temp[g[0]][g[1]] = "👻"
    temp[player_pos[0]][player_pos[1]] = "🤖" + DIRECTION_SYMBOLS.get(direction, '')
    for row in temp:
        st.markdown("".join(row))

# -------------------- 게임 로직 -------------------- #
def apply_commands(commands, grid, player_pos, targets, portals, ghost_pos, level_config):
    visited_targets = set()
    for cmd in commands:
        steps = 1
        if " " in cmd:
            cmd, step = cmd.split()
            steps = int(step)
        for _ in range(steps):
            dx, dy = DIRECTIONS.get(cmd, (0, 0))
            new_x, new_y = player_pos[0] + dx, player_pos[1] + dy
            if 0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE and grid[new_x][new_y] != "⬛":
                player_pos = [new_x, new_y]
            for p1, p2 in portals:
                if tuple(player_pos) == p1:
                    player_pos = list(p2)
                elif tuple(player_pos) == p2:
                    player_pos = list(p1)
            for g in ghost_pos:
                move_ghost(g, player_pos, grid, level_config.get("ghost_blocked", False))
            if player_pos in ghost_pos:
                return player_pos, visited_targets, True
            if player_pos in targets:
                visited_targets.add(tuple(player_pos))
    return player_pos, visited_targets, False

def move_ghost(g, target, grid, blocked):
    dx = target[0] - g[0]
    dy = target[1] - g[1]
    move_x = 1 if dx > 0 else -1 if dx < 0 else 0
    move_y = 1 if dy > 0 else -1 if dy < 0 else 0
    for dx, dy in [(move_x, 0), (0, move_y)]:
        nx, ny = g[0] + dx, g[1] + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            if blocked and grid[nx][ny] == "⬛":
                continue
            g[0], g[1] = nx, ny
            break

# -------------------- Streamlit 인터페이스 -------------------- #
st.set_page_config(layout="wide")
init_ranking_db()

if "level" not in st.session_state:
    st.session_state.level = list(LEVELS.keys())[0]
if "map_data" not in st.session_state:
    st.session_state.map_data = generate_map(LEVELS[st.session_state.level])
if "commands_input" not in st.session_state:
    st.session_state.commands_input = ""

st.title("🤖 로봇 명령 퍼즐 게임")

col1, col2 = st.columns([3, 2])
with col1:
    st.markdown("### 🎮 게임 화면")
    grid, player_pos, targets, portals, obstacles, ghost_pos = st.session_state.map_data
    render(grid, player_pos, ghost_pos, "")

with col2:
    st.markdown("### ⚙️ 명령어 입력")
    level = st.selectbox("난이도 선택", list(LEVELS.keys()), index=list(LEVELS.keys()).index(st.session_state.level))
    if st.button("🔁 다시 시작"):
        st.session_state.level = level
        st.session_state.map_data = generate_map(LEVELS[level])
        st.session_state.commands_input = ""
    commands_input = st.text_area("명령어를 한 줄에 쉼표로 구분해 입력 (예: 앞으로, 오른쪽 2, 왼쪽)", value=st.session_state.commands_input)
    st.session_state.commands_input = commands_input
    if st.button("▶️ 실행"):
        commands = [cmd.strip() for cmd in commands_input.split(",")]
        player_pos, visited, is_dead = apply_commands(commands, *st.session_state.map_data, LEVELS[level])
        score = LEVELS[level]["score"] if len(visited) == 2 and not is_dead else 0
        st.success(f"획득 점수: {score}점" + (" 🎯 Perfect!" if len(visited) == 2 and not is_dead else " ❌ 실패"))
        name = st.text_input("이름을 입력하고 Enter로 저장", key="name_input")
        if name and score > 0:
            save_score(name, score)
            st.success("랭킹에 저장되었습니다!")

if st.button("🏆 랭킹 보기"):
    st.markdown("### 🥇 랭킹")
    for idx, (name, score) in enumerate(get_rankings(), 1):
        st.markdown(f"{idx}위 - {name}: {score}점")
""")

full_code

