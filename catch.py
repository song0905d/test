# streamlit_app.py
import streamlit as st
import random
import time
import traceback
from collections import deque
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="🤖 로봇 명령 퍼즐", page_icon="🤖", layout="centered")

import sqlite3

conn = sqlite3.connect("robot_game_runs.db")
cur = conn.cursor()
cur.execute("DELETE FROM runs WHERE user_id = ?", ("최동혁 사라져",))
conn.commit()
conn.close()


# (선택) 배경 음악 – 자동 재생은 브라우저에서 막힐 수 있어서 controls 추가
bgm_html = """
<audio controls loop>
  <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
  브라우저가 audio 태그를 지원하지 않습니다.
</audio>
"""

st.markdown(bgm_html, unsafe_allow_html=True)


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

LEVEL_NAMES = list(LEVELS.keys())
LEVEL_DIFFICULTY = {name: i + 1 for i, name in enumerate(LEVEL_NAMES)}  # 난이도 1~5

# ----------------------------- DB ----------------------------- #
def get_conn():
    conn = sqlite3.connect("robot_game_runs.db", check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            run_time TEXT,
            level TEXT,
            difficulty INTEGER,
            commands TEXT,
            success INTEGER,
            steps INTEGER,
            optimal_steps INTEGER
        );
        """
    )
    conn.commit()
    return conn

def log_run(conn, user_id, level, difficulty, commands, success, steps, optimal_steps):
    """한 판 결과 기록"""
    if not user_id:
        return
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO runs (user_id, run_time, level, difficulty, commands, success, steps, optimal_steps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            datetime.now().isoformat(timespec="seconds"),
            level,
            difficulty,
            commands,
            int(success),
            steps,
            optimal_steps if optimal_steps is not None else None,
        ),
    )
    conn.commit()

def get_user_stats(conn, user_id, k=20):
    """개인 최근 k판 기준 성공률 / 마지막 난이도"""
    if not user_id:
        return None
    cur = conn.cursor()
    cur.execute(
        """
        SELECT difficulty, success
        FROM runs
        WHERE user_id = ?
        ORDER BY run_time DESC
        LIMIT ?
        """,
        (user_id, k),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    n = len(rows)
    success_rate = sum(r[1] for r in rows) / n
    last_diff = rows[0][0]
    return {
        "n": n,
        "success_rate": success_rate,
        "last_diff": last_diff,
    }

def recommend_level_name(stats):
    """개인 맞춤 레벨 추천"""
    if stats is None or stats["n"] < 5:
        return LEVEL_NAMES[0]  # 데이터 적으면 1레벨
    diff = stats["last_diff"]
    sr = stats["success_rate"]
    if sr > 0.8 and diff < 5:
        diff += 1
    elif sr < 0.4 and diff > 1:
        diff -= 1
    return LEVEL_NAMES[diff - 1]

def load_runs_df(conn):
    return pd.read_sql_query(
        "SELECT id, user_id, run_time, level, difficulty, success, steps, optimal_steps, commands FROM runs ORDER BY run_time DESC",
        conn,
    )

# ----------------------------- 유틸/로직 ----------------------------- #
def bfs_shortest_path(start, goals, obstacles):
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        if current in goals:
            return path
        for d in MOVE_OFFSET.values():
            nx, ny = current[0] + d[0], current[1] + d[1]
            nxt = (nx, ny)
            if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE and nxt not in obstacles and nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))
    return []

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
    if rotation_command == "오른쪽 회전":
        return DIRECTIONS[(idx + 1) % 4]
    elif rotation_command == "왼쪽 회전":
        return DIRECTIONS[(idx - 1) % 4]
    return current_direction

def move_forward(pos, direction, steps=1):
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
        target_dir = None
        for dir_name, (dx_off, dy_off) in MOVE_OFFSET.items():
            if (dx, dy) == (dx_off, dy_off):
                target_dir = dir_name
                break
        if target_dir is None:
            continue

        if direction == target_dir:
            forward_count += 1
        else:
            flush_forward()
            while direction != target_dir:
                cur_idx = DIRECTIONS.index(direction)
                tgt_idx = DIRECTIONS.index(target_dir)
                if (tgt_idx - cur_idx) % 4 == 1:
                    cmds.append("오른쪽 회전")
                    direction = rotate(direction, "오른쪽 회전")
                else:
                    cmds.append("왼쪽 회전")
                    direction = rotate(direction, "왼쪽 회전")
            forward_count = 1

    flush_forward()
    cmds.append("집기")
    return cmds

def _rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

# ----------------------------- 앱 시작 ----------------------------- #
conn = get_conn()

st.title("🤖 로봇 명령 퍼즐 게임")

# 배경 음악
st.markdown(
    """
    <audio autoplay loop>
        <source src="https://www.bensound.com/bensound-music/bensound-littleidea.mp3" type="audio/mpeg">
    </audio>
    """,
    unsafe_allow_html=True
)

# 사용자 ID + 통계
user_id = st.text_input("사용자 ID (학번 또는 닉네임)", key="user_id")
user_stats = get_user_stats(conn, user_id, k=20)

c_info = st.columns(3)
with c_info[0]:
    st.metric("최근 기록 수", user_stats["n"] if user_stats else 0)
with c_info[1]:
    st.metric("최근 성공률", f"{user_stats['success_rate']*100:.1f}%" if user_stats else "-")
with c_info[2]:
    rec_level = recommend_level_name(user_stats) if user_stats else LEVEL_NAMES[0]
    st.metric("추천 레벨", rec_level)

st.caption("추천 레벨은 최근 성공률을 바탕으로 개인 맞춤으로 결정됩니다. 필요하면 아래에서 직접 다른 레벨을 선택해도 됩니다.")

# 상태 초기화
if "state" not in st.session_state:
    default_level = rec_level if user_stats else LEVEL_NAMES[0]
    level_info = LEVELS[default_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, start[0] + level_info.get('ghost_range', 0)), start[1]) if level_info['ghost'] else None
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

# command_input 상태 변수 (위젯 key로 쓰지 않음)
if "command_input" not in st.session_state:
    st.session_state["command_input"] = ""

# 레벨 선택
current_level = st.session_state.state['level']
selected_level = st.selectbox("레벨 선택", LEVEL_NAMES, index=LEVEL_NAMES.index(current_level))
if selected_level != st.session_state.state['level']:
    level_info = LEVELS[selected_level]
    start, obstacles, goals, portals = generate_map(level_info['obstacles'], use_portals=level_info.get('portals', False))
    ghost = (min(MAP_SIZE - 1, start[0] + level_info.get('ghost_range', 0)), start[1]) if level_info['ghost'] else None
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

# 입력창 (위젯에 key 안 줌, value로만 연결)
input_text = st.text_area(
    "명령어 입력(한 줄에 하나씩)",
    value=st.session_state["command_input"]
)
# 사용자가 바꾼 값을 다시 상태에 반영
st.session_state["command_input"] = input_text

# 간단 보정 + 리스트화
fixed = []
for line in input_text.strip().split('\n'):
    s = line.strip()
    if s == "앞":
        s = "앞으로"
    if s:
        fixed.append(s)
command_list = fixed

# 자동완성
auto_options = ["앞으로", "앞으로 2", "앞으로 3", "왼쪽으로 이동", "오른쪽으로 이동", "뒤로 이동", "집기"]
c1, c2 = st.columns([2, 1])
with c1:
    chosen = st.selectbox("자동완성 명령어 선택", auto_options, index=0)
with c2:
    if st.button("➕ 추가"):
        cur = st.session_state.get("command_input", "")
        st.session_state["command_input"] = cur + ("\n" if cur else "") + chosen
        _rerun()

# 실행 버튼
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
                parts = cmd.split()
                steps = 1
                if len(parts) > 1:
                    num = parts[1]
                    if num.endswith("칸"):
                        num = num[:-1]
                    if num.isdigit():
                        steps = int(num)
                for _ in range(steps):
                    tmp = move_forward(pos, direction, 1)
                    if tmp is None or tmp in s['obstacles']:
                        s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                        failed = True
                        break
                    pos = tmp

            elif cmd == "왼쪽으로 이동":
                left_dir = DIRECTIONS[(DIRECTIONS.index(direction) - 1) % 4]
                tmp = move_forward(pos, left_dir, 1)
                if tmp is None or tmp in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = tmp

            elif cmd == "오른쪽으로 이동":
                right_dir = DIRECTIONS[(DIRECTIONS.index(direction) + 1) % 4]
                tmp = move_forward(pos, right_dir, 1)
                if tmp is None or tmp in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = tmp

            elif cmd == "뒤로 이동":
                back_dir = DIRECTIONS[(DIRECTIONS.index(direction) + 2) % 4]
                tmp = move_forward(pos, back_dir, 1)
                if tmp is None or tmp in s['obstacles']:
                    s['result'] = '❌ 장애물 충돌 또는 벽 밖으로 벗어남'
                    failed = True
                    break
                pos = tmp

            elif cmd in ("왼쪽 회전", "오른쪽 회전"):
                direction = rotate(direction, cmd)

            elif cmd == "집기" and pos in s['goals']:
                visited_goals.add(pos)

            if failed:
                break

            # 귀신 이동
            if ghost:
                ghost = move_ghost(ghost, pos, s['obstacles'],
                                   ignore_obstacles=LEVELS[s['level']].get('ignore_obstacles', False))
                ghost_path.append(ghost)
                if pos == ghost:
                    s['result'] = '👻 귀신에게 잡힘!'
                    failed = True
                    break

            # 맵 그리기 + 딜레이
            draw_grid(pos, direction, ghost, ghost_path, s['obstacles'], s['goals'], s['portals'])
            time.sleep(0.2)

            # 포탈 처리
            if s['portals'] and pos in s['portals']:
                dest = [p for p in s['portals'] if p != pos][0]
                around = [(dest[0] + d[0], dest[1] + d[1]) for d in MOVE_OFFSET.values()]
                random.shuffle(around)
                for a in around:
                    if 0 <= a[0] < MAP_SIZE and 0 <= a[1] < MAP_SIZE and a not in s['obstacles']:
                        pos = a
                        break

        success_flag = False
        if not failed:
            score = len(visited_goals) * LEVELS[s['level']]['score']
            s['score'] = score
            s['total_score'] += score
            s['high_score'] = max(s['high_score'], score)
            s['result'] = f"🎯 목표 도달: {len(visited_goals)}개, 점수: {score}"

            shortest = bfs_shortest_path(s['start'], s['goals'], s['obstacles'])
            if shortest and len(command_list) == len(shortest) + 2 and len(visited_goals) == 2:
                s['result'] += '\n🌟 Perfect!'

            # 목표 1개 이상 집으면 성공 판정
            success_flag = len(visited_goals) > 0

        s.update({
            'position': pos,
            'direction': direction,
            'ghost': ghost,
            'ghost_path': ghost_path,
            'commands': command_list
        })

        # 기록 저장용 steps / optimal_steps
        steps = len(command_list)
        optimal_steps = None
        try:
            shortest_for_log = bfs_shortest_path(s['start'], s['goals'], s['obstacles'])
            if shortest_for_log:
                optimal_steps = len(shortest_for_log) + 2  # 집기 2번 포함 가정
        except Exception:
            optimal_steps = None

        log_run(
            conn=conn,
            user_id=user_id,
            level=s['level'],
            difficulty=LEVEL_DIFFICULTY[s['level']],
            commands='\n'.join(command_list),
            success=success_flag,
            steps=steps,
            optimal_steps=optimal_steps,
        )

    except Exception:
        st.error("실행 중 예외가 발생했습니다. 아래 로그를 확인하세요.")
        st.code(traceback.format_exc())

# 상태 + 맵 표시
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
    ghost = (min(MAP_SIZE - 1, start[0] + level_info.get('ghost_range', 0)), start[1]) if level_info['ghost'] else None
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
    _rerun()

# 설명
with st.expander("📘 게임 설명"):
    st.markdown("""
- 기본설정은 위쪽을 바라보고 있습니다.
- `앞으로`, `앞으로 2`, `앞으로 3칸` 등 전진
- `왼쪽으로 이동` / `오른쪽으로 이동` / `뒤로 이동` (현재 바라보는 방향 기준 상대 이동)
- `집기` (현재 칸이 🎯일 때)
- '귀신'은 플레이어의 명렁어 하나 당 플레이어를 향해 한칸씩 이동합니다.
""")

# AI 힌트
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

# ----------------------------- 기록 / 통계 ----------------------------- #
st.markdown("---")
st.subheader("📊 명령어 기록 / 통계")

df = load_runs_df(conn)
if df.empty:
    st.info("아직 저장된 기록이 없습니다. 먼저 게임을 플레이해 주세요.")
else:
    user_options = ["전체"] + sorted([u for u in df["user_id"].dropna().unique().tolist() if u])
    selected_user = st.selectbox("사용자 선택", user_options, key="log_user")
    level_options = ["전체"] + LEVEL_NAMES
    selected_level_for_log = st.selectbox("레벨 선택", level_options, key="log_level")

    filtered = df.copy()
    if selected_user != "전체":
        filtered = filtered[filtered["user_id"] == selected_user]
    if selected_level_for_log != "전체":
        filtered = filtered[filtered["level"] == selected_level_for_log]

    st.dataframe(
        filtered[["id", "user_id", "run_time", "level", "difficulty", "success", "steps", "optimal_steps", "commands"]],
        use_container_width=True,
        height=300,
    )

    if not filtered.empty:
        steps_mean = filtered["steps"].mean()
        steps_std = filtered["steps"].std(ddof=1) if len(filtered) > 1 else 0.0
        success_rate = filtered["success"].mean()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("명령어 수 평균", f"{steps_mean:.3f}")
        with c2:
            st.metric("명령어 수 표준편차", f"{steps_std:.3f}")
        with c3:
            st.metric("성공률", f"{success_rate*100:.1f}%")

        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="현재 데이터 CSV 다운로드",
            data=csv,
            file_name="robot_game_runs.csv",
            mime="text/csv",
        )
