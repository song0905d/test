# 로봇 명령 퍼즐 게임 - 완성 코드
import streamlit as st
import random
import time
from collections import deque

# 설정
MAP_SIZE = 10
DIRECTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT']
DIRECTION_SYMBOLS = {'UP': '↑', 'RIGHT': '→', 'DOWN': '↓', 'LEFT': '←'}
MOVE_OFFSET = {'UP': (-1, 0), 'DOWN': (1, 0), 'LEFT': (0, -1), 'RIGHT': (0, 1)}
PORTAL_SYMBOL = '🌀'

LEVELS = {
    "Level 1 (5점, 착한맛)": {"obstacles": 8, "score": 5, "ghost": False},
    "Level 2 (10점, 보통맛)": {"obstacles": 14, "score": 10, "ghost": False},
    "Level 3 (20점, 매운맛)": {"obstacles": 20, "score": 20, "ghost": False},
    "Level 4 (30점, 불닭맛)": {"obstacles": 22, "score": 30, "ghost": True, "ghost_range": 7, "ignore_obstacles": False},
    "Level 5 (50점, 핵불닭맛)": {"obstacles": 25, "score": 50, "ghost": True, "ghost_range": 5, "ignore_obstacles": True, "portals": True},
}

# 맵 생성
def generate_map(obstacle_count, goal_count=2, use_portals=False):
    while True:
        all_pos = [(i, j) for i in range(MAP_SIZE) for j in range(MAP_SIZE)]
        start = random.choice(all_pos)
        all_pos.remove(start)

        obstacles = set(random.sample(all_pos, obstacle_count))
        all_pos = [p for p in all_pos if p not in obstacles]

        goals = random.sample(all_pos, goal_count)
        all_pos = [p for p in all_pos if p not in goals]

        portals = random.sample(all_pos, 2) if use_portals else []

        if all(bfs_shortest_path(start, [g], obstacles) for g in goals):
            break
    return start, obstacles, goals, portals

# 회전
def rotate(dir, cmd):
    idx = DIRECTIONS.index(dir)
    return DIRECTIONS[(idx + 1) % 4] if "오른쪽" in cmd else DIRECTIONS[(idx - 1) % 4]

# 이동
def move_forward(pos, dir, steps):
    for _ in range(steps):
        offset = MOVE_OFFSET[dir]
        pos = (pos[0] + offset[0], pos[1] + offset[1])
        if not (0 <= pos[0] < MAP_SIZE and 0 <= pos[1] < MAP_SIZE):
            return None
    return pos

# 귀신 이동
def move_ghost(pos, target, obstacles, ignore=False):
    dx, dy = target[0] - pos[0], target[1] - pos[1]
    options = []
    if dx != 0:
        options.append((pos[0] + (1 if dx > 0 else -1), pos[1]))
    if dy != 0:
        options.append((pos[0], pos[1] + (1 if dy > 0 else -1)))
    for opt in options:
        if 0 <= opt[0] < MAP_SIZE and 0 <= opt[1] < MAP_SIZE:
            if ignore or opt not in obstacles:
                return opt
    return pos

# BFS 최단경로
def bfs_shortest_path(start, goals, obstacles):
    q = deque([(start, [])])
    visited = {start}
    while q:
        cur, path = q.popleft()
        if cur in goals:
            return path
        for d in MOVE_OFFSET.values():
            nx, ny = cur[0] + d[0], cur[1] + d[1]
            nxt = (nx, ny)
            if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE and nxt not in visited and nxt not in obstacles:
                visited.add(nxt)
                q.append((nxt, path + [nxt]))
    return []

# 맵 출력
def draw_map(pos, dir, ghost, ghost_path, obs, goals, portals):
    grid = ""
    for i in range(MAP_SIZE):
        for j in range(MAP_SIZE):
            if (i, j) == pos:
                grid += '🤡' + DIRECTION_SYMBOLS[dir]
            elif (i, j) in obs:
                grid += '⬛'
            elif (i, j) in goals:
                grid += '🎯'
            elif (i, j) == ghost:
                grid += '👻'
            elif (i, j) in ghost_path:
                grid += '·'
            elif (i, j) in portals:
                grid += PORTAL_SYMBOL
            else:
                grid += '⬜'
        grid += '\n'
    st.text(grid)

# 초기화
st.title("🤖 로봇 명령 퍼즐 게임")
st.markdown("명령어: 앞으로 / 앞으로 2 / 왼쪽 회전 / 오른쪽 회전 / 집기")

if 'game' not in st.session_state:
    default = list(LEVELS.keys())[0]
    cfg = LEVELS[default]
    start, obs, goals, portals = generate_map(cfg['obstacles'], use_portals=cfg.get('portals', False))
    ghost_range = cfg.get('ghost_range', 0)
    ghost = (min(MAP_SIZE - 1, start[0] + ghost_range), start[1]) if cfg['ghost'] else None
    st.session_state.game = {
        'level': default,
        'start': start,
        'pos': start,
        'dir': 'UP',
        'obs': obs,
        'goals': goals,
        'portals': portals,
        'ghost': ghost,
        'ghost_path': [],
        'score': 0,
        'high': 0,
        'total': 0,
        'result': '',
        'cmds': []
    }

# 레벨 선택
sel = st.selectbox("레벨", list(LEVELS.keys()))
if sel != st.session_state.game['level']:
    cfg = LEVELS[sel]
    start, obs, goals, portals = generate_map(cfg['obstacles'], use_portals=cfg.get('portals', False))
    ghost_range = cfg.get('ghost_range', 0)
    ghost = (min(MAP_SIZE - 1, start[0] + ghost_range), start[1]) if cfg['ghost'] else None
    st.session_state.game.update({
        'level': sel, 'start': start, 'pos': start, 'dir': 'UP',
        'obs': obs, 'goals': goals, 'portals': portals,
        'ghost': ghost, 'ghost_path': [], 'result': '', 'cmds': []
    })

# 명령 실행
cmd_input = st.text_area("명령어 입력 (줄바꿈)")
if st.button("실행"):
    g = st.session_state.game
    pos, dir, ghost = g['start'], 'UP', g['ghost']
    visited, failed, g_path = set(), False, []
    cmds = cmd_input.strip().split('\n')

    for cmd in cmds:
        st.write(f"명령어: `{cmd}`")
        if cmd.startswith("앞으로"):
            step = int(cmd.split()[1]) if len(cmd.split()) > 1 else 1
            for _ in range(step):
                new = move_forward(pos, dir, 1)
                if new is None or new in g['obs']:
                    g['result'] = "❌ 장애물 충돌/맵 밖!"
                    failed = True
                    break
                pos = new
        elif "회전" in cmd:
            dir = rotate(dir, cmd)
        elif cmd == "집기" and pos in g['goals']:
            visited.add(pos)

        if failed:
            break

        if ghost:
            ghost = move_ghost(ghost, pos, g['obs'], ignore=LEVELS[g['level']].get('ignore_obstacles', False))
            g_path.append(ghost)
            if ghost == pos:
                g['result'] = "👻 귀신에게 잡힘!"
                failed = True
                break

        if pos in g['obs']:
            g['result'] = "❌ 장애물 충돌!"
            failed = True
            break

        draw_map(pos, dir, ghost, g_path, g['obs'], g['goals'], g['portals'])
        time.sleep(0.5)

        if pos in g['portals']:
            dest = [p for p in g['portals'] if p != pos][0]
            options = [(dest[0]+dx, dest[1]+dy) for dx, dy in MOVE_OFFSET.values()]
            random.shuffle(options)
            for o in options:
                if 0 <= o[0] < MAP_SIZE and 0 <= o[1] < MAP_SIZE:
                    pos = o
                    break

    if not failed:
        score = len(visited) * LEVELS[g['level']]['score']
        g['score'] = score
        g['total'] += score
        g['high'] = max(g['high'], score)
        g['result'] = f"🎯 {len(visited)}개 도달! 점수: {score}"

        if len(cmds) == len(bfs_shortest_path(g['start'], g['goals'], g['obs'])) + 2 and len(visited) == 2:
            g['result'] += "\n🌟 Perfect!"

    g.update({'pos': pos, 'dir': dir, 'ghost': ghost, 'ghost_path': g_path, 'cmds': cmds})

# 출력
g = st.session_state.game
st.markdown(f"**현재 점수:** {g['score']} / **최고 점수:** {g['high']} / **누적:** {g['total']}")
st.markdown(f"**결과:** {g['result']}")
draw_map(g['pos'], g['dir'], g['ghost'], g['ghost_path'], g['obs'], g['goals'], g['portals'])

if st.button("🔁 다시 시작"):
    cfg = LEVELS[g['level']]
    start, obs, goals, portals = generate_map(cfg['obstacles'], use_portals=cfg.get('portals', False))
    ghost_range = cfg.get('ghost_range', 0)
    ghost = (min(MAP_SIZE - 1, start[0] + ghost_range), start[1]) if cfg['ghost'] else None
    g.update({
        'start': start, 'pos': start, 'dir': 'UP',
        'obs': obs, 'goals': goals, 'portals': portals,
        'ghost': ghost, 'ghost_path': [], 'result': '', 'cmds': []
    })

st.markdown(
    """
    <audio autoplay loop>
        <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
    </audio>
    """,
    unsafe_allow_html=True
)

