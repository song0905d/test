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

        portals = []
        if use_portals:
            portals = random.sample(positions, 2)

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

if 'state' not in st.session_state:
    default_level = list(LEVELS.keys())[0]
    level_info = LEVELS[default_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost = None
    if level_info['ghost']:
        ghost = (min(MAP_SIZE - 1, start[0] + level_info['ghost_range']), start[1])
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

selected_level = st.selectbox("레벨 선택", list(LEVELS.keys()))
if selected_level != st.session_state.state['level']:
    level_info = LEVELS[selected_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost = None
    if level_info['ghost']:
        ghost = (min(MAP_SIZE - 1, start[0] + level_info['ghost_range']), start[1])
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
    st.session_state["command_input"] = ""  # ✅ 명확하게 초기화

commands = st.text_area("명령어 입력(한줄에 명령어 하나씩)", value=st.session_state.get('command_input', ''))

if st.button("실행"):
    s = st.session_state.state
    pos = s['position']
    direction = s['direction']
    ghost = s['ghost']
    ghost_path = []
    visited_goals = set()
    failed = False

    command_list = commands.strip().split('\n')
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

        draw_grid(pos, direction, ghost, ghost_path, s['obstacles'], s['goals'], s['portals'])
        time.sleep(0.3)

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
    st.session_state['command_input'] = '\n'.join(command_list)

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
    ghost = None
    if level_info['ghost']:
        ghost = (min(MAP_SIZE - 1, start[0] + level_info['ghost_range']), start[1])
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

with st.expander("📘 게임 설명 보기"):
    st.markdown("""
    ### 🎮 게임 방법
    로봇 🤡에게 명령어를 입력하여 두 개의 🎯 목표 지점에 도달하고 집기 명령으로 수집하세요!  
    장애물(⬛)을 피하고, 귀신(👻)에게 잡히지 않도록 조심하세요!

    ### ✏️ 사용 가능한 명령어 (기본 방향 위)
    - 편의를 위한 자동완성 명령어 기능 존재
    - 앞으로 : 한 칸 전진
    - 앞으로 2, 앞으로 3 : 여러 칸 전진
    - 왼쪽으로 이동 : 왼쪽 방향으로 1칸 이동
    - 오른쪽으로 이동 : 오른쪽 방향으로 1칸 이동
    - 집기 : 현재 칸에 목표물이 있을 경우 수집

    ### 🌀 포탈
    - 포탈(🌀)에 들어가면 다른 포탈 근처 랜덤 위치로 순간 이동
    - 귀신은 포탈을 사용할 수 없음

    ### 👻 귀신
    - 레벨 4: 귀신은 장애물을 피해서 이동
    - 레벨 5: 귀신은 장애물을 무시하고 직진 추적

    ### 🏆 Perfect 판정
    - 최단 경로 + 모든 목표 수집 + 명령 수 최소일 때 Perfect! 🌟

    ### 🧱 각 레벨 정보
    - Level 1 (5점, 착한맛): 장애물 8개, 귀신 없음
    - Level 2 (10점, 보통맛): 장애물 14개, 귀신 없음
    - Level 3 (20점, 매운맛): 장애물 20개, 귀신 없음
    - Level 4 (30점, 불닭맛): 장애물 24개, 귀신 1명
    - Level 5 (50점, 핵불닭맛): 장애물 28개, 귀신 1명, 포탈 2개

    -오류 발견시 문의
    """)

# 🔊 배경음악 삽입
st.markdown(
    """
    <audio autoplay loop>
        <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
    </audio>
    """,
    unsafe_allow_html=True
)


# 명령어 자동완성 옵션 UI
auto_options = ["앞으로", "앞으로 2", "앞으로 3", "왼쪽 회전", "오른쪽 회전", "집기"]
selected_command = st.selectbox("자동완성 명령어 선택", auto_options)
if st.button("➕ 명령어 추가"):
    current = st.session_state.get("command_input", "")
    new_value = (current + "\n" + selected_command).strip()
    st.session_state["command_input"] = new_value

# 명령어 입력창 (자동완성과 연동)
commands = st.text_area("명령어 입력(한줄에 명령어 하나씩)",
                        value=st.session_state.get("command_input", ""),
                        key="command_input")

# 입력 보정: "앞" → "앞으로"
corrected_lines = []
for line in commands.strip().split('\n'):
    stripped = line.strip()
    if stripped == "앞":
        corrected_lines.append("앞으로")
    else:
        corrected_lines.append(stripped)
commands = "\n".join(corrected_lines)



# 경로 → 명령어 변환 함수
def path_to_commands(path, initial_direction='UP'):
    commands = []
    direction = initial_direction

    for i in range(1, len(path)):
        cur = path[i - 1]
        nxt = path[i]
        dx, dy = nxt[0] - cur[0], nxt[1] - cur[1]

        # 이동 방향 계산
        for dir_name, (dx_offset, dy_offset) in MOVE_OFFSET.items():
            if (dx, dy) == (dx_offset, dy_offset):
                target_dir = dir_name
                break

def path_to_commands(path, initial_direction='UP'):
    commands = []
    direction = initial_direction

    for i in range(1, len(path)):
        cur = path[i - 1]
        nxt = path[i]
        dx, dy = nxt[0] - cur[0], nxt[1] - cur[1]

        for dir_name, (dx_offset, dy_offset) in MOVE_OFFSET.items():
            if (dx, dy) == (dx_offset, dy_offset):
                target_dir = dir_name
                break

        rotate_cmds = []
        orig_direction = direction  # 현재 바라보는 방향 저장

        while direction != target_dir:
            cur_idx = DIRECTIONS.index(direction)
            target_idx = DIRECTIONS.index(target_dir)
            if (target_idx - cur_idx) % 4 == 1:
                rotate_cmds.append("오른쪽으로 이동")
                direction = rotate(direction, "오른쪽 회전")
            else:
                rotate_cmds.append("왼쪽으로 이동")
                direction = rotate(direction, "왼쪽 회전")

        commands.extend(rotate_cmds)
        commands.append("앞으로")

        # 방향 복원
        while direction != orig_direction:
            cur_idx = DIRECTIONS.index(direction)
            orig_idx = DIRECTIONS.index(orig_direction)
            if (orig_idx - cur_idx) % 4 == 1:
                commands.append("오른쪽으로 이동")
                direction = rotate(direction, "오른쪽 회전")
            else:
                commands.append("왼쪽으로 이동")
                direction = rotate(direction, "왼쪽 회전")

    commands.append("집기")
    return commands
# AI 힌트 버튼 처리
if st.button("\U0001f9e0 AI 힌트 보기 (-30점)"):
    s = st.session_state.state

    if s['total_score'] < 30:
        st.warning("포인트가 부족합니다! 최소 30점 이상 필요해요.")
    else:
        path = None
        for goal in s['goals']:
            path = bfs_shortest_path(s['position'], [goal], s['obstacles'])
            if path:
                break

        if not path:
            st.error("경로를 찾을 수 없습니다.")
        else:
            s['total_score'] -= 30
            ai_commands = path_to_commands([s['position']] + path, s['direction'])
            st.info("**AI 추천 명령어:**\n\n" + '\n'.join(ai_commands))

 
