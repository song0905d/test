import streamlit as st
import random
import time
from collections import deque

# ----------------------------- 설정 ----------------------------- #
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
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

        # 시작→각 목표로 경로가 있는 경우만 채택
        if all(bfs_shortest_path(start, [g], obstacles) for g in goals):
            break

    return start, obstacles, goals, portals

def rotate(current_direction, rotation_command):
    idx = DIRECTIONS.index(current_direction)
    if rotation_command == "오른쪽 회전":
        return DIRECTIONS[(idx + 1) % 4]
    elif rotation_command == "왼쪽 회전":
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
        nonlocal forward_count
        if forward_count == 1:
            cmds.append("앞으로")
        elif forward_count > 1:
            cmds.append(f"앞으로 {forward_count}칸")
        forward_count = 0

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
            # 회전
            while direction != target_dir:
                cur_idx = DIRECTIONS.index(direction)
                target_idx = DIRECTIONS.index(target_dir)
                if (target_idx - cur_idx) % 4 == 1:
                    cmds.append("오른쪽 회전")
                    direction = rotate(direction, "오른쪽 회전")
                else:
                    cmds.append("왼쪽 회전")
                    direction = rotate(direction, "왼쪽 회전")
            forward_count = 1

    flush_forward()
    cmds.append("집기")
    return cmds

# ----------------------------- 실행 ----------------------------- #
st.title("🤖 로봇 명령 퍼즐 게임")

st.markdown(
    """
    <audio autoplay loop>
        <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
    </audio>
    """,
    unsafe_allow_html=True
)

# 초기 상태
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
    st.session_state['command_input'] = ""

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

# ✅ 입력창: 페이지에 한 번만!
input_text = st.text_area(
    "명령어 입력(한 줄에 하나씩)",
    value=st.session_state.get('command_input', ''),
    key="command_input"
)

# 간단 보정(“앞” -> “앞으로”)
lines = []
for line in input_text.strip().split('\n'):
    s = line.strip()
    lines.append("앞으로" if s == "앞" else s)
input_text = "\n".join(lines)

# ✅ 들여쓰기 없이 바로 리스트로 변환
command_list = [c for c in input_text.split('\n') if c.strip()]

# 자동완성(입력창은 추가 생성하지 않음)
auto_options = ["앞으로", "앞으로 2", "앞으로 3", "왼쪽 회전", "오른쪽 회전", "왼쪽으로 이동", "오른쪽으로 이동", "뒤로 이동", "집기"]
col1, col2 = st.columns([2,1])
with col1:
    selected_command = st.selectbox("자동완성 명령어 선택", auto_options, index=0)
with col2:
    if st.button("➕ 추가"):
        cur = st.session_state.get("command_input", "")
        st.session_state["command_input"] = (cur + ("\n" if cur else "") + selected_command)
        st.experimental_rerun()

# 실행
if st.button("실행"):
    try:
        s = st.session_state.state
        pos = s['position']
        direction = s['direction']
        ghost = s['ghost']
        ghost_path = []
        visited_goals = set()
        failed = False

        for raw in command_list:
            cmd = raw.strip()
            if not cmd:
                continue

            if cmd.startswith("앞으로"):
                # "앞으로 3" 또는 "앞으로 3칸" 모두 지원
                parts = cmd.split()
                steps = 1
                if len(parts) > 1:
                    num = parts[1]
                    if num.endswith("칸"):
                        num = num[:-1]
                    if num.isdigit():
                        steps = int(num)
                for _ in range(steps):
                    temp_pos = move_forward(pos, direction, 1)
                    if temp_pos is None or temp_pos in s['obstacles']:
                        s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                        failed = True
                        break
                    pos = temp_pos

            elif cmd == "왼쪽으로 이동":
                left_dir = DIRECTIONS[(DIRECTIONS.index(direction) - 1) % 4]
                temp_pos = move_forward(pos, left_dir, 1)
                if temp_pos is None or temp_pos in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = temp_pos

            elif cmd == "오른쪽으로 이동":
                right_dir = DIRECTIONS[(DIRECTIONS.index(direction) + 1) % 4]
                temp_pos = move_forward(pos, right_dir, 1)
                if temp_pos is None or temp_pos in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = temp_pos

            elif cmd == "뒤로 이동":
                back_dir = DIRECTIONS[(DIRECTIONS.index(direction) + 2) % 4]
                temp_pos = move_forward(pos, back_dir, 1)
                if temp_pos is None or temp_pos in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = temp_pos

            elif cmd in ("왼쪽 회전", "오른쪽 회전"):
                direction = rotate(direction, cmd)

            elif cmd == "집기" and pos in s['goals']:
                visited_goals.add(pos)

            if failed:
                break

            # 귀신
            if ghost:
                ghost = move_ghost(ghost, pos, s['obstacles'], ignore_obstacles=LEVELS[s['level']].get('ignore_obstacles', False))
                ghost_path.append(ghost)
                if pos == ghost:
                    s['result'] = '👻 귀신에게 잡힘!'
                    failed = True
                    break

            draw_grid(pos, direction, ghost, ghost_path, s['obstacles'], s['goals'], s['portals'])
            time.sleep(0.2)

            # 포탈
            if s['portals'] and pos in s['portals']:
                dest = [p for p in s['portals'] if p != pos][0]
                around = [(dest[0] + d[0], dest[1] + d[1]) for d in MOVE_OFFSET.values()]
                random.shuffle(around)
                for a in around:
                    if 0 <= a[0] < MAP_SIZE and 0 <= a[1] < MAP_SIZE and a not in s['obstacles']:
                        pos = a
                        break

        if not failed:
            score = len(visited_goals) * LEVELS[s['level']]['score']
            s['score'] = score
            s['total_score'] += score
            s['high_score'] = max(s['high_score'], score)
            s['result'] = f"🎯 목표 도달: {len(visited_goals)}개, 점수: {score}"

            shortest = bfs_shortest_path(s['start'], s['goals'], s['obstacles'])
            if shortest and len(command_list) == len(shortest) + 2 and len(visited_goals) == 2:
                s['result'] += '\n🌟 Perfect!'

        s.update({
            'position': pos,
            'direction': direction,
            'ghost': ghost,
            'ghost_path': ghost_path,
            'commands': command_list
        })
        st.session_state['command_input'] = '\n'.join(command_list)

    except Exception as e:
        import traceback
        st.error("예외가 발생했습니다. 아래 로그를 공유해 주세요.")
        st.code(traceback.format_exc())

# 상태 표시
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

# 다시 시작
if st.button("🔁 다시 시작"):
    level_info = LEVELS[st.session_state.state['level']]
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
        'commands': []
    })
    st.session_state['command_input'] = ""

# 설명
with st.expander("📘 게임 설명 보기"):
    st.markdown("""
    - `앞으로`, `앞으로 2`, `앞으로 3칸` 등 전진
    - `왼쪽 회전` / `오른쪽 회전` (방향만 전환)
    - `왼쪽으로 이동` / `오른쪽으로 이동` / `뒤로 이동` (현재 바라보는 방향 기준 상대 이동)
    - `집기` (현재 칸이 🎯일 때)
    """)

# AI 힌트 (선택)
if st.button("🧠 AI 힌트 보기 (-30점)"):
    s = st.session_state.state
    if s['total_score'] < 30:
        st.warning("포인트가 부족합니다! (30점 필요)")
    else:
        path = None
        for g in s['goals']:
            p = bfs_shortest_path(s['position'], [g], s['obstacles'])
            if p:
                path = p
                break
        if not path:
            st.error("경로를 찾을 수 없습니다.")
        else:
            s['total_score'] -= 30
            hint = path_to_commands([s['position']] + path, s['direction'])
            st.info("**AI 추천 명령어**\n\n" + "\n".join(hint))
