import streamlit as st
import random
import time
from collections import deque

# ----------------------------- 설정 ----------------------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 5, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 9, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 13, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
}
MAP_SIZE = 10  # 9x9보다 한 칸씩 늘림
PORTAL_SYMBOL = '🌀'

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

        # 모든 목표 도달 가능한지 확인
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
            elif (i, j) in ghost_path:
                cell = '·'
            elif (i, j) in portals:
                cell = PORTAL_SYMBOL
            grid += cell
        grid += '\n'
    st.text(grid)

# ----------------------------- 실행 ----------------------------- #
st.title("🤖 로봇 명령 퍼즐 게임")
st.markdown("""
- 명령어 예시:
    - 앞으로
    - 앞으로 2
    - 앞으로 3
    - 왼쪽 회전
    - 오른쪽 회전
    - 집기
""")

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

selected_level = st.selectbox("레벨 선택", list(LEVELS.keys()))
if selected_level != st.session_state.state['level']:
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

commands = st.text_area("명령어 입력 (줄바꿈으로 분리)")
if st.button("실행"):
    s = st.session_state.state
    pos = s['start']
    direction = 'UP'
    ghost = s['ghost']
    ghost_path = []
    visited_goals = set()
    failed = False

    command_list = commands.strip().split('\n')
    for cmd in command_list:
        st.write(f"➡️ 명령어: `{cmd}`")
        cmd = cmd.strip()
        if cmd.startswith("앞으로"):
            steps = int(cmd.split()[1]) if len(cmd.split()) > 1 else 1
            for step in range(1, steps+1):
                temp_pos = move_forward(pos, direction, 1)
                if temp_pos is None or temp_pos in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = temp_pos
        elif "회전" in cmd:
            direction = rotate(direction, cmd)
        elif cmd == "집기" and pos in s['goals']:
            visited_goals.add(pos)

        if failed:
            break

        if ghost:
            ghost = move_ghost(ghost, pos, s['obstacles'], ignore_obstacles=LEVELS[s['level']].get('ignore_obstacles', False))
            ghost_path.append(ghost)
            if pos == ghost:
                s['result'] = '👻 귀신에게 잡힘!'
                failed = True
                break

        if pos in s['obstacles']:
            s['result'] = '❌ 장애물에 충돌!'
            failed = True
            break

        draw_grid(pos, direction, ghost, ghost_path, s['obstacles'], s['goals'], s['portals'])
        time.sleep(0.4)

        # 포탈 처리
        if pos in s['portals']:
            dest = [p for p in s['portals'] if p != pos][0]
            around = [(dest[0] + d[0], dest[1] + d[1]) for d in MOVE_OFFSET.values()]
            random.shuffle(around)
            for a in around:
                if 0 <= a[0] < MAP_SIZE and 0 <= a[1] < MAP_SIZE:
                    pos = a
                    break

    if not failed:
        score = len(visited_goals) * LEVELS[s['level']]['score']
        s['score'] = score
        s['total_score'] += score
        s['high_score'] = max(s['high_score'], score)
        s['result'] = f"🎯 목표 도달: {len(visited_goals)}개, 점수: {score}"

        shortest = bfs_shortest_path(s['start'], s['goals'], s['obstacles'])
        if len(command_list) == len(shortest) + 2 and len(visited_goals) == 2:
            s['result'] += '\n🌟 Perfect!'

    s.update({
        'position': pos,
        'direction': direction,
        'ghost': ghost,
        'ghost_path': ghost_path,
        'commands': command_list
    })

st.markdown(f"**현재 점수:** {st.session_state.state['score']} / **최고 점수:** {st.session_state.state['high_score']} / **누적 점수:** {st.session_state.state['total_score']}")
st.markdown(f"**결과:** {st.session_state.state['result']}")

draw_grid(
    st.session_state.state['position'],
    st.session_state.state['direction'],
    st.session_state.state['ghost'],
    st.session_state.state['ghost_path'],
    st.session_state.state['obstacles'],
    st.session_state.state['goals'],
    st.session_state.state['portals']
)

if st.button("🔁 다시 시작"):
    level_info = LEVELS[st.session_state.state['level']]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost_range = level_info.get('ghost_range', 0)
    ghost = (min(MAP_SIZE - 1, start[0] + ghost_range), start[1]) if level_info['ghost'] else None
    st.session_state.state.update({
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
