import streamlit as st
import random
import time
import pandas as pd
from collections import deque
import os

# -------------------- 설정 -------------------- #
MAP_SIZE = 9
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
PORTAL_SYMBOL = '🌀'
RANK_FILE = 'rankings.csv'

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
}

# -------------------- 초기화 -------------------- #
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
            break

    return start, obstacles, goals, portals

# -------------------- 이동 관련 함수 -------------------- #
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

def move_ghost(pos, target, obstacles, ignore_obstacles):
    dx, dy = target[0] - pos[0], target[1] - pos[1]
    options = []
    if dx != 0: options.append((pos[0] + (1 if dx > 0 else -1), pos[1]))
    if dy != 0: options.append((pos[0], pos[1] + (1 if dy > 0 else -1)))
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

# -------------------- UI 출력 -------------------- #
def draw_grid(position, direction, ghost, ghost_path, obstacles, goals, portals):
    grid = ""
    for i in range(MAP_SIZE):
        for j in range(MAP_SIZE):
            cell = '⬜'
            if (i, j) == position:
                cell = '🤡' + DIRECTION_SYMBOLS[direction]
            elif (i, j) in obstacles:
                cell = '⬛'
            elif (i, j) in goals:
                cell = '🎯'
            elif (i, j) == ghost:
                cell = '👻'
            elif (i, j) in portals:
                cell = PORTAL_SYMBOL
            elif (i, j) in ghost_path:
                cell = '·'
            grid += cell
        grid += '\n'
    st.text(grid)

# -------------------- 랭킹 -------------------- #
def save_score(name, score):
    if os.path.exists(RANK_FILE):
        df = pd.read_csv(RANK_FILE)
    else:
        df = pd.DataFrame(columns=['Name', 'Score'])
    df = pd.concat([df, pd.DataFrame([[name, score]], columns=['Name', 'Score'])])
    df.to_csv(RANK_FILE, index=False)

def show_rankings():
    if os.path.exists(RANK_FILE):
        df = pd.read_csv(RANK_FILE).sort_values(by='Score', ascending=False).head(10)
        st.subheader("🏆 랭킹 TOP 10")
        st.dataframe(df)
    else:
        st.info("아직 등록된 랭킹이 없습니다.")

# -------------------- 실행 -------------------- #
st.title("🤖 로봇 명령 퍼즐 게임")
st.markdown("""
명령어 예시: 앞으로, 앞으로 2, 앞으로 3, 왼쪽 회전, 오른쪽 회전, 집기
""")

# 배경음악 추가
st.markdown("""
<audio autoplay loop>
  <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mp3">
</audio>
""", unsafe_allow_html=True)

# 설명서
with st.expander("📘 게임 설명서"):
    st.markdown("""
        ### 🎮 게임 방법
    로봇 🤡에게 명령어를 입력하여 두 개의 🎯 목표 지점을 방문하고 `집기` 명령으로 수집하세요!  
    장애물(⬛)을 피하고, 귀신(👻)에게 잡히지 않도록 조심하세요!

    ### ✏️ 사용 가능한 명령어
    - `앞으로` : 한 칸 전진
    - `앞으로 2`, `앞으로 3` : 여러 칸 전진
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

# 상태 초기화
if 'state' not in st.session_state:
    default_level = list(LEVELS.keys())[0]
    info = LEVELS[default_level]
    s, obs, goals, portals = generate_map(info['obstacles'], use_portals=info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, s[0] + info.get('ghost_range', 0)), s[1]) if info.get('ghost') else None
    st.session_state.state = {
        'level': default_level, 'start': s, 'position': s, 'direction': 'UP',
        'obstacles': obs, 'goals': goals, 'portals': portals,
        'ghost': ghost, 'ghost_path': [], 'score': 0,
        'high_score': 0, 'total_score': 0, 'result': '', 'commands': []
    }

# 레벨 변경 시 맵 유지
level = st.selectbox("레벨 선택", list(LEVELS.keys()), index=list(LEVELS.keys()).index(st.session_state.state['level']))
if level != st.session_state.state['level']:
    info = LEVELS[level]
    s, obs, goals, portals = generate_map(info['obstacles'], use_portals=info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, s[0] + info.get('ghost_range', 0)), s[1]) if info.get('ghost') else None
    st.session_state.state.update({
        'level': level, 'start': s, 'position': s, 'direction': 'UP',
        'obstacles': obs, 'goals': goals, 'portals': portals,
        'ghost': ghost, 'ghost_path': [], 'result': '', 'commands': []
    })

commands = st.text_area("명령어 입력 (줄바꿈)")

# 실행
if st.button("실행"):
    s = st.session_state.state
    pos, direction = s['start'], 'UP'
    ghost, ghost_path, visited_goals = s['ghost'], [], set()
    failed = False
    cmds = commands.strip().split('\n')

    for cmd in cmds:
        st.write(f"➡️ `{cmd}`")
        cmd = cmd.strip()
        if cmd.startswith("앞으로"):
            steps = int(cmd.split()[1]) if len(cmd.split()) > 1 else 1
            for _ in range(steps):
                temp = move_forward(pos, direction, 1)
                if temp is None or temp in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로!'
                    failed = True
                    break
                pos = temp
        elif "회전" in cmd:
            direction = rotate(direction, cmd)
        elif cmd == "집기" and pos in s['goals']:
            visited_goals.add(pos)

        if failed: break

        if ghost:
            ghost = move_ghost(ghost, pos, s['obstacles'], LEVELS[s['level']].get('ignore_obstacles', False))
            ghost_path.append(ghost)
            if pos == ghost:
                s['result'] = '👻 귀신에게 잡힘!'
                failed = True
                break

        if pos in s['obstacles']:
            s['result'] = '❌ 장애물에 부딪힘!'
            failed = True
            break

        if pos in s['portals']:
            dest = [p for p in s['portals'] if p != pos][0]
            around = [(dest[0]+d[0], dest[1]+d[1]) for d in MOVE_OFFSET.values()]
            random.shuffle(around)
            for a in around:
                if 0 <= a[0] < MAP_SIZE and 0 <= a[1] < MAP_SIZE:
                    pos = a
                    break

        draw_grid(pos, direction, ghost, ghost_path, s['obstacles'], s['goals'], s['portals'])
        time.sleep(0.4)

    if not failed:
        score = len(visited_goals) * LEVELS[s['level']]['score']
        s.update({'score': score, 'total_score': s['total_score']+score, 'high_score': max(s['high_score'], score)})
        s['result'] = f"🎯 목표 {len(visited_goals)}개 도달! 점수: {score}"

        shortest = bfs_shortest_path(s['start'], s['goals'], s['obstacles'])
        if len(cmds) == len(shortest) + 2 and len(visited_goals) == 2:
            s['result'] += '\n🌟 Perfect!'

    s.update({'position': pos, 'direction': direction, 'ghost': ghost, 'ghost_path': ghost_path, 'commands': cmds})

# 출력
st.markdown(f"**현재 점수:** {st.session_state.state['score']} / **최고 점수:** {st.session_state.state['high_score']} / **누적 점수:** {st.session_state.state['total_score']}")
st.markdown(f"**결과:** {st.session_state.state['result']}")

# 랭킹 저장
if st.button("🏅 랭킹 등록"):
    name = st.text_input("이름을 입력하세요:", key="name_input")
    if name:
        save_score(name, st.session_state.state['score'])
        st.success("랭킹에 등록되었습니다!")

if st.button("📊 랭킹 보기"):
    show_rankings()

# 다시 시작
if st.button("🔁 다시 시작"):
    info = LEVELS[st.session_state.state['level']]
    s, obs, goals, portals = generate_map(info['obstacles'], use_portals=info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, s[0] + info.get('ghost_range', 0)), s[1]) if info.get('ghost') else None
    st.session_state.state.update({
        'start': s, 'position': s, 'direction': 'UP',
        'obstacles': obs, 'goals': goals, 'portals': portals,
        'ghost': ghost, 'ghost_path': [], 'result': '', 'commands': []
    })
