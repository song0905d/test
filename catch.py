import streamlit as st
import random
import time
from collections import deque

# ----------------------------- 설정 ----------------------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 24, "score": 30, "ghost": True, "ghost_range": 4, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 28, "score": 50, "ghost": True, "ghost_range": 3, "ignore_obstacles": True, "portals": True},
}
MAP_SIZE = 9
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
        portals = random.sample(positions, 2) if use_portals else []

        if all(bfs_shortest_path(start, [g], obstacles) for g in goals):
            break
    return start, obstacles, goals, portals

def rotate(current_direction, rotation_command):
    idx = DIRECTIONS.index(current_direction)
    if "오른쪽" in rotation_command:
        return DIRECTIONS[(idx + 1) % 4]
    elif "왼쪽" in rotation_command:
        return DIRECTIONS[(idx - 1) % 4]
    return current_direction

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
                cell = '🤡'
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

def path_to_commands(path, initial_direction='UP'):
    cmds = []
    direction = initial_direction
    forward_count = 0

    def flush_forward():
        if forward_count == 1:
            cmds.append("앞으로")
        elif forward_count > 1:
            cmds.append(f"앞으로 {forward_count}칸")

    for i in range(1, len(path)):
        cur = path[i - 1]
        nxt = path[i]
        dx, dy = nxt[0] - cur[0], nxt[1] - cur[1]
        for dir_name, (dx_offset, dy_offset) in MOVE_OFFSET.items():
            if (dx, dy) == (dx_offset, dy_offset):
                target_dir = dir_name
                break

        if direction == target_dir:
            forward_count += 1
        else:
            flush_forward()
            forward_count = 0
            while direction != target_dir:
                cur_idx = DIRECTIONS.index(direction)
                target_idx = DIRECTIONS.index(target_dir)
                if (target_idx - cur_idx) % 4 == 1:
                    cmds.append("오른쪽으로 이동")
                    direction = rotate(direction, "오른쪽 회전")
                else:
                    cmds.append("왼쪽으로 이동")
                    direction = rotate(direction, "왼쪽 회전")
            forward_count = 1

    flush_forward()
    cmds.append("집기")
    return cmds

# ----------------------------- Streamlit 실행 ----------------------------- #
st.title("🤖 로봇 명령 퍼즐 게임")

# 배경음악
st.markdown(
    """
    <audio autoplay loop>
        <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
    </audio>
    """,
    unsafe_allow_html=True
)

# 초기화
if 'state' not in st.session_state:
    default_level = list(LEVELS.keys())[0]
    level_info = LEVELS[default_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, start[0] + level_info['ghost_range']), start[1]) if level_info['ghost'] else None
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
    st.session_state["command_input"] = ""

# 레벨 선택
selected_level = st.selectbox("레벨 선택", list(LEVELS.keys()))
if selected_level != st.session_state.state['level']:
    level_info = LEVELS[selected_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, start[0] + level_info['ghost_range']), start[1]) if level_info['ghost'] else None
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
    st.session_state["command_input"] = ""

# 입력창
input_text = st.text_area("명령어 입력", value=st.session_state.get("command_input", ""), key="command_input")

# 입력 보정
corrected_lines = []
for line in input_text.strip().split('\n'):
    corrected_lines.append("앞으로" if line.strip() == "앞" else line.strip())
input_text = "\n".join(corrected_lines)
command_list = input_text.strip().split('\n')

# 명령 실행
if st.button("실행"):
    s = st.session_state.state
    pos = s['position']
    direction = s['direction']
    ghost = s['ghost']
    ghost_path = []
    visited_goals = set()
    failed = False

    for cmd in command_list:
        if cmd.startswith("앞으로"):
            steps = int(cmd.split()[1]) if len(cmd.split()) > 1 else 1
            for _ in range(steps):
                temp_pos = move_forward(pos, direction, 1)
                if temp_pos is None or temp_pos in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = temp_pos

        elif cmd == "뒤로 이동":
            temp_pos = move_forward(pos, 'DOWN', 1)
            if temp_pos is None or temp_pos in s['obstacles']:
                s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                failed = True
                break
            pos = temp_pos

        elif "회전" in cmd:
            direction = rotate(direction, cmd)

        elif cmd == "왼쪽으로 이동":
            temp_pos = move_forward(pos, 'LEFT', 1)
            if temp_pos is None or temp_pos in s['obstacles']:
                s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                failed = True
                break
            pos = temp_pos

        elif cmd == "오른쪽으로 이동":
            temp_pos = move_forward(pos, 'RIGHT', 1)
            if temp_pos is None or temp_pos in s['obstacles']:
                s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                failed = True
                break
            pos = temp_pos

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

        draw_grid(pos, direction, ghost, ghost_path, s['obstacles'], s['goals'], s['portals'])
        time.sleep(0.3)

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
    st.session_state['command_input'] = '\n'.join(command_list)

# 결과 표시
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
# 다시 시작 버튼
if st.button("🔁 다시 시작"):
    s = st.session_state.state
    level_info = LEVELS[s['level']]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, start[0] + level_info['ghost_range']), start[1]) if level_info['ghost'] else None
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
        'commands': [],
        'score': 0
    })
    st.session_state["command_input"] = ""

# AI 힌트 버튼
if st.button("💡 AI 힌트 보기"):
    shortest = bfs_shortest_path(
        st.session_state.state['start'],
        st.session_state.state['goals'],
        st.session_state.state['obstacles']
    )
    if shortest:
        st.markdown("🧠 **최적 경로 예시**")
        for step in shortest:
            st.markdown(f"- 앞으로 이동 → {step}")
    else:
        st.warning("최적 경로를 찾을 수 없습니다.")

# 명령어 입력 예시
with st.expander("📋 명령어 예시 보기"):
    st.markdown("""
    - `앞으로` → 한 칸 전진  
    - `앞으로 2` 또는 `앞으로 3` → 여러 칸 전진  
    - `왼쪽 회전`, `오른쪽 회전` → 방향 전환  
    - `왼쪽으로 이동`, `오른쪽으로 이동`, `뒤로 이동`  
    - `집기` → 목표 지점에서 아이템 줍기  
    """)

# 게임 설명
with st.expander("📘 게임 설명"):
    st.markdown("""
    - 이 게임은 명령어를 입력하여 🤡 캐릭터를 움직이고, 🎯 목표 지점에 도달하여 점수를 획득하는 로봇 퍼즐 게임입니다.  
    - 각 레벨은 점점 어려워지고, 귀신 👻이나 장애물 🟥, 포탈 🌀 등이 등장합니다.  
    - Perfect 판정은 최단 거리로 명령어를 입력하고 모든 목표에 도달하면 부여됩니다.
    """)

# 도움말
with st.expander("🧠 명령어 자동 완성 도움말"):
    st.markdown("""
    명령어 입력 시 다음과 같은 형식으로 입력하세요.
    ```
    앞으로 2
    오른쪽 회전
    앞으로 1
    집기
    ```
    """)

