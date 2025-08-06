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
PORTAL_SYMBOL = '🌀'
MAP_SIZE = 9

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
    "Level 6 (100점, 지옥맛)": {"obstacles": 30, "score": 100, "ghost": True, "ghost_count": 3, "ignore_obstacles": True, "portals": True},
}

# ----------------------------- DB 초기화 ----------------------------- #
def init_ranking_db():
    conn = sqlite3.connect("ranking.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ranking (
        name TEXT,
        score INTEGER,
        level TEXT,
        timestamp TEXT
    )''')
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
    result = c.fetchall()
    conn.close()
    return result

init_ranking_db()

# ----------------------------- 기본 함수 ----------------------------- #
def generate_map(obstacle_count, goal_count=2, use_portals=False):
    while True:
        all_positions = [(i, j) for i in range(MAP_SIZE) for j in range(MAP_SIZE)]
        start = random.choice(all_positions)
        all_positions.remove(start)

        obstacles = set(random.sample(all_positions, obstacle_count))
        available = [p for p in all_positions if p not in obstacles]

        goals = random.sample(available, goal_count)
        remaining = [p for p in available if p not in goals]

        portals = []
        if use_portals:
            portals = random.sample(remaining, 2)

        if all(bfs_shortest_path(start, [g], obstacles) for g in goals):
            break

    return start, obstacles, goals, portals

def rotate(direction, turn):
    idx = DIRECTIONS.index(direction)
    return DIRECTIONS[(idx + 1) % 4] if "오른쪽" in turn else DIRECTIONS[(idx - 1) % 4]

def move_forward(pos, direction, steps):
    for _ in range(steps):
        dx, dy = MOVE_OFFSET[direction]
        pos = (pos[0] + dx, pos[1] + dy)
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
            np = (nx, ny)
            if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE and np not in visited and np not in obstacles:
                visited.add(np)
                queue.append((np, path + [np]))
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

# ----------------------------- 상태 초기화 ----------------------------- #
def reset_game(level_name, keep_map=False):
    info = LEVELS[level_name]
    if not keep_map:
        start, obstacles, goals, portals = generate_map(info['obstacles'], use_portals=info.get('portals', False))
    else:
        start = st.session_state['start']
        obstacles = st.session_state['obstacles']
        goals = st.session_state['goals']
        portals = st.session_state['portals']

    ghosts = []
    if info.get("ghost_count", 0) > 0:
        directions = list(MOVE_OFFSET.values())
        for i in range(info["ghost_count"]):
            dx, dy = directions[i]
            gx, gy = start[0] + dx, start[1] + dy
            if 0 <= gx < MAP_SIZE and 0 <= gy < MAP_SIZE:
                ghosts.append((gx, gy))
    elif info.get("ghost", False):
        ghost_range = info.get("ghost_range", 0)
        ghosts = [(min(MAP_SIZE - 1, start[0] + ghost_range), start[1])]

    st.session_state.update({
        'level': level_name,
        'start': start,
        'position': start,
        'direction': 'UP',
        'obstacles': obstacles,
        'goals': goals,
        'portals': portals,
        'ghosts': ghosts,
        'ghost_path': [],
        'score': 0,
        'result': '',
        'commands': [],
        'input_text': ""
    })

# ----------------------------- UI ----------------------------- #
st.title("🤖 로봇 명령 퍼즐 게임")
st.markdown("""
<audio autoplay loop>
    <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
</audio>
""", unsafe_allow_html=True)

if 'level' not in st.session_state:
    reset_game("Level 1 (5점, 착한맛)")

selected_level = st.selectbox("레벨 선택", list(LEVELS.keys()))
if selected_level != st.session_state['level']:
    reset_game(selected_level)

if st.button("🔁 다시 시작"):
    reset_game(st.session_state['level'], keep_map=True)

# 명령어 입력창
input_text = st.text_area("명령어 입력 (한 줄에 하나씩)", value=st.session_state.get('input_text', ''), key="input_area")

if st.button("실행"):
    s = st.session_state
    pos = s['position']
    direction = s['direction']
    ghosts = s['ghosts']
    ghost_path = []
    visited_goals = set()
    failed = False

    command_list = input_text.strip().split('\n')
    for cmd in command_list:
        if cmd.startswith("앞으로"):
            steps = int(cmd.split()[1]) if len(cmd.split()) > 1 else 1
            for _ in range(steps):
                temp = move_forward(pos, direction, 1)
                if temp is None or temp in s['obstacles']:
                    s['result'] = "❌ 충돌 또는 벽 넘음"
                    failed = True
                    break
                pos = temp
        elif "회전" in cmd:
            direction = rotate(direction, cmd)
        elif cmd == "집기" and pos in s['goals']:
            visited_goals.add(pos)

        if failed:
            break

        new_ghosts = []
        for g in ghosts:
            g2 = move_ghost(g, pos, s['obstacles'], ignore_obstacles=LEVELS[s['level']].get('ignore_obstacles', False))
            if g2 == pos:
                s['result'] = "👻 귀신에게 잡힘!"
                failed = True
                break
            new_ghosts.append(g2)
        ghosts = new_ghosts
        ghost_path.extend(ghosts)

        draw_grid(pos, direction, ghosts, ghost_path, s['obstacles'], s['goals'], s['portals'])
        time.sleep(0.2)

        if pos in s['portals']:
            others = [p for p in s['portals'] if p != pos]
            if others:
                dest = others[0]
                around = [(dest[0] + dx, dest[1] + dy) for dx, dy in MOVE_OFFSET.values()]
                for a in around:
                    if 0 <= a[0] < MAP_SIZE and 0 <= a[1] < MAP_SIZE:
                        pos = a
                        break

    if not failed:
        score = len(visited_goals) * LEVELS[s['level']]['score']
        s['score'] = score
        s['result'] = f"🎯 도달: {len(visited_goals)}개, 점수: {score}"
        if len(command_list) == len(bfs_shortest_path(s['start'], s['goals'], s['obstacles'])) + 2:
            s['result'] += "\n🌟 Perfect!"

        if score > 0:
            name = st.text_input("이름을 입력하세요 (랭킹 저장)", key="save_name")
            if name:
                save_score(name, score, s['level'])
                st.success("랭킹 저장 완료!")

    s.update({
        'position': pos,
        'direction': direction,
        'ghosts': ghosts,
        'ghost_path': ghost_path,
        'commands': command_list,
        'input_text': ""
    })



if st.button("🏆 랭킹 보기"):
    rows = load_ranking()
    st.markdown("### 🏅 TOP 10")
    for i, r in enumerate(rows, 1):
        st.write(f"{i}위 | 이름: {r[0]} | 점수: {r[1]} | 레벨: {r[2]} | 시간: {r[3]}")
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
