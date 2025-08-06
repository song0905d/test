import streamlit as st
import random
import time
from collections import deque

# ----------------------------- 설정 ----------------------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
PORTAL_SYMBOL = '🌀'
MAP_SIZE = 9  # 줄임

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
}

# ----------------------------- 초기화 ----------------------------- #
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.level = list(LEVELS.keys())[0]
    st.session_state.position = None
    st.session_state.direction = 'UP'
    st.session_state.score = 0
    st.session_state.high_score = 0
    st.session_state.total_score = 0
    st.session_state.result = ''
    st.session_state.commands = []
    st.session_state.ghost = None
    st.session_state.ghost_path = []

    def reset_map(level):
        level_info = LEVELS[level]
        while True:
            all_pos = [(i, j) for i in range(MAP_SIZE) for j in range(MAP_SIZE)]
            start = random.choice(all_pos)
            all_pos.remove(start)
            obstacles = set(random.sample(all_pos, level_info["obstacles"]))
            all_pos = [p for p in all_pos if p not in obstacles]
            goals = random.sample(all_pos, 2)
            all_pos = [p for p in all_pos if p not in goals]
            portals = random.sample(all_pos, 2) if level_info.get("portals") else []
            if all(bfs_shortest_path(start, [g], obstacles) for g in goals):
                break
        ghost_range = level_info.get('ghost_range', 0)
        ghost = (max(0, start[0] - ghost_range), start[1]) if level_info.get("ghost") else None
        st.session_state.position = start
        st.session_state.start = start
        st.session_state.obstacles = obstacles
        st.session_state.goals = goals
        st.session_state.portals = portals
        st.session_state.ghost = ghost
        st.session_state.ghost_path = []

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

    def draw_grid():
        grid = ""
        for i in range(MAP_SIZE):
            for j in range(MAP_SIZE):
                p = (i, j)
                if p == st.session_state.position:
                    grid += '🤡' + DIRECTION_SYMBOLS[st.session_state.direction]
                elif p in st.session_state.obstacles:
                    grid += '⬛'
                elif p in st.session_state.goals:
                    grid += '🎯'
                elif p == st.session_state.ghost:
                    grid += '👻'
                elif p in st.session_state.ghost_path:
                    grid += '·'
                elif p in st.session_state.portals:
                    grid += PORTAL_SYMBOL
                else:
                    grid += '⬜'
            grid += '\n'
        st.text(grid)

    reset_map(st.session_state.level)

# ----------------------------- UI ----------------------------- #
col1, col2 = st.columns([2, 1])
with col1:
    st.title("🤖 로봇 명령 퍼즐 게임")

# ✅ 배경음악 삽입
st.markdown("""
<audio autoplay loop>
  <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mp3">
Your browser does not support the audio element.
</audio>
""", unsafe_allow_html=True)

    
    level = st.selectbox("레벨 선택", list(LEVELS.keys()), index=list(LEVELS.keys()).index(st.session_state.level))
    if level != st.session_state.level:
        st.session_state.level = level
        reset_map(level)

with col2:
    with st.expander("📘 게임 설명서"):
        st.markdown("""
        - 🤡: 로봇 (방향 표시 포함)
        - 🎯: 목표 지점 (2개)
        - ⬛: 장애물 (충돌 시 게임 오버)
        - 👻: 귀신 (레벨 4, 5에 등장)
        - 🌀: 포탈 (레벨 5에서만 등장, 플레이어만 이용 가능)
        - 회전 명령: `왼쪽 회전`, `오른쪽 회전`
        - 이동 명령: `앞으로`, `앞으로 2`, `앞으로 3`
        - 목표 획득 명령: `집기`
        """)

commands = st.text_area("명령어 입력 (줄바꿈으로 구분)")
if st.button("실행"):
    pos = st.session_state.start
    direction = 'UP'
    ghost = st.session_state.ghost
    ghost_path = []
    visited_goals = set()
    failed = False
    cmds = commands.strip().split('\n')

    for cmd in cmds:
        st.write(f"🛠 명령어: `{cmd}`")
        cmd = cmd.strip()
        if cmd.startswith("앞으로"):
            parts = cmd.split()
            steps = int(parts[1]) if len(parts) > 1 else 1
            for _ in range(steps):
                offset = MOVE_OFFSET[direction]
                next_pos = (pos[0] + offset[0], pos[1] + offset[1])
                if not (0 <= next_pos[0] < MAP_SIZE and 0 <= next_pos[1] < MAP_SIZE):
                    st.session_state.result = "❌ 범위 밖으로 이동!"
                    failed = True
                    break
                if next_pos in st.session_state.obstacles:
                    st.session_state.result = "❌ 장애물에 부딪힘!"
                    failed = True
                    break
                pos = next_pos
        elif "회전" in cmd:
            idx = DIRECTIONS.index(direction)
            if cmd == "오른쪽 회전":
                direction = DIRECTIONS[(idx + 1) % 4]
            else:
                direction = DIRECTIONS[(idx - 1) % 4]
        elif cmd == "집기" and pos in st.session_state.goals:
            visited_goals.add(pos)

        if failed:
            break

        # 포탈
        if pos in st.session_state.portals:
            others = [p for p in st.session_state.portals if p != pos]
            if others:
                dest = others[0]
                around = [(dest[0]+dx, dest[1]+dy) for dx, dy in MOVE_OFFSET.values()]
                random.shuffle(around)
                for a in around:
                    if 0 <= a[0] < MAP_SIZE and 0 <= a[1] < MAP_SIZE:
                        pos = a
                        break

        # 귀신
        if ghost:
            gx, gy = ghost
            px, py = pos
            dx, dy = px - gx, py - gy
            moves = []
            if dx != 0:
                moves.append((gx + (1 if dx > 0 else -1), gy))
            if dy != 0:
                moves.append((gx, gy + (1 if dy > 0 else -1)))
            for m in moves:
                if 0 <= m[0] < MAP_SIZE and 0 <= m[1] < MAP_SIZE:
                    if LEVELS[st.session_state.level].get("ignore_obstacles", False) or m not in st.session_state.obstacles:
                        ghost = m
                        break
            ghost_path.append(ghost)
            if ghost == pos:
                st.session_state.result = "👻 귀신에게 잡혔습니다!"
                failed = True
                break

        draw_grid()
        time.sleep(0.4)

    if not failed:
        score = len(visited_goals) * LEVELS[st.session_state.level]["score"]
        st.session_state.score = score
        st.session_state.total_score += score
        st.session_state.high_score = max(st.session_state.high_score, score)
        st.session_state.result = f"🎯 목표 도달: {len(visited_goals)}개 / 점수: {score}"
        if len(visited_goals) == 2 and len(cmds) <= len(bfs_shortest_path(st.session_state.start, st.session_state.goals, st.session_state.obstacles)) + 2:
            st.session_state.result += "\n🌟 Perfect!"

    st.session_state.position = pos
    st.session_state.direction = direction
    st.session_state.ghost = ghost
    st.session_state.ghost_path = ghost_path

# ----------------------------- 출력 ----------------------------- #
st.markdown(f"**현재 점수:** {st.session_state.score} / **최고 점수:** {st.session_state.high_score} / **누적 점수:** {st.session_state.total_score}")
st.markdown(f"**결과:** {st.session_state.result}")
draw_grid()

if st.button("🔁 다시 시작"):
    reset_map(st.session_state.level)


with st.expander("📘 게임 설명서 보기"):
    st.markdown("""
    ### 🎮 게임 방법
    로봇 🤡에게 명령어를 입력하여 두 개의 🎯 목표 지점을 방문하고 `집기` 명령으로 수집하세요!  
    장애물(⬛)을 피하고, 귀신(👻)에게 잡히지 않도록 조심하세요!

    ### ✏️ 사용 가능한 명령어
    - `앞으로` : 한 칸 전진
    - `앞으로2`, `앞으로3` : 여러 칸 전진
    - `왼쪽 회전` : 반시계 방향으로 90도 회전
    - `오른쪽 회전` : 시계 방향으로 90도 회전
    - `집기` : 현재 칸에 목표물이 있을 경우 수집

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
