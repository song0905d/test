import streamlit as st
import random
import time
import pandas as pd

# 방향 설정
direction_symbols = ['↑', '→', '↓', '←']
dx = [-1, 0, 1, 0]
dy = [0, 1, 0, -1]

if 'score_log' not in st.session_state:
    st.session_state.score_log = []

# 맵 생성 함수
def create_map(level):
    size = 8
    grid = [['⬜' for _ in range(size)] for _ in range(size)]
    all_positions = [(i, j) for i in range(size) for j in range(size)]

    start_pos = random.choice(all_positions)
    all_positions.remove(start_pos)

    goal1 = random.choice(all_positions)
    all_positions.remove(goal1)

    goal2 = random.choice(all_positions)
    all_positions.remove(goal2)

    base_obstacles = {1: 5, 2: 10, 3: 15}
    num_obstacles = base_obstacles.get(level, 5) + 4  # +4 장애물

    obstacle_pos = random.sample(all_positions, num_obstacles)

    start_dir = random.randint(0, 3) if level >= 2 else 0

    grid[start_pos[0]][start_pos[1]] = direction_symbols[start_dir]
    grid[goal1[0]][goal1[1]] = '🎯'
    grid[goal2[0]][goal2[1]] = '🎯'
    for ox, oy in obstacle_pos:
        if (ox, oy) not in [start_pos, goal1, goal2]:
            grid[ox][oy] = '🧱'

    return grid, start_pos, start_dir, [goal1, goal2], set(obstacle_pos)

# 격자 출력
def render_grid(grid):
    for row in grid:
        st.markdown(''.join(row))

# 명령어 해석 및 실행
def move_robot(grid, pos, direction, commands, goal_positions, obstacles, level):
    x, y = pos
    size = len(grid)
    score = 0
    reached_goals = set()

    for cmd in commands:
        grid[x][y] = '⬜'

        if cmd.startswith('앞으로'):
            parts = cmd.split()
            steps = 1
            if len(parts) == 2 and parts[1].isdigit():
                steps = int(parts[1])
            for _ in range(steps):
                nx, ny = x + dx[direction], y + dy[direction]
                if 0 <= nx < size and 0 <= ny < size:
                    if (nx, ny) in obstacles:
                        score -= 2
                    else:
                        x, y = nx, ny
        elif cmd == '오른쪽 회전':
            direction = (direction + 1) % 4
        elif cmd == '왼쪽 회전':
            direction = (direction - 1) % 4
        elif cmd == '집기':
            if (x, y) in goal_positions and (x, y) not in reached_goals:
                reached_goals.add((x, y))
                grid[x][y] = '✅'
                level_score = {1: 5, 2: 10, 3: 20}
                score += level_score.get(level, 5)

        grid[x][y] = direction_symbols[direction]

    success = len(reached_goals) == len(goal_positions)
    return grid, success, score, (x, y, direction)

# UI
st.title("🤖 로봇 퍼즐 게임 v2 - 다중 목표 & 다중 이동")

level = st.selectbox("레벨 선택", [1, 2, 3], format_func=lambda x: f"Level {x}")

if st.button("🔁 게임 다시 시작"):
    st.session_state.grid, st.session_state.pos, st.session_state.dir, st.session_state.goals, st.session_state.obstacles = create_map(level)
    st.session_state.score = 0

# 최초 실행 시 초기화
if 'grid' not in st.session_state:
    st.session_state.grid, st.session_state.pos, st.session_state.dir, st.session_state.goals, st.session_state.obstacles = create_map(level)
    st.session_state.score = 0
    st.session_state.max_score = 0
    st.session_state.total_score = 0

st.markdown(f"### 🧮 현재 점수: {st.session_state.score}")
st.markdown(f"### 🏆 최고 점수: {st.session_state.max_score}")
st.markdown(f"### 📊 누적 점수: {st.session_state.total_score}")

render_grid(st.session_state.grid)

commands_input = st.text_area("명령어 입력 (예: 앞으로 2, 오른쪽 회전, 집기)", height=150)
commands = [line.strip() for line in commands_input.strip().split('\n') if line.strip()]

if st.button("명령어 실행"):
    start_time = time.time()
    st.write("⏱ 15초 제한 - 명령 실행 중...")
    grid, success, delta_score, final_state = move_robot(
        st.session_state.grid,
        st.session_state.pos,
        st.session_state.dir,
        commands,
        st.session_state.goals,
        st.session_state.obstacles,
        level
    )
    elapsed = time.time() - start_time

    if elapsed > 15:
        st.error(f"⏰ 제한 시간 초과! ({elapsed:.2f}초)")
        delta_score = 0
        success = False
    else:
        st.success(f"✅ 명령어 처리 완료 ({elapsed:.2f}초)")

    st.session_state.score += delta_score
    st.session_state.total_score += delta_score
    if st.session_state.score > st.session_state.max_score:
        st.session_state.max_score = st.session_state.score

    x, y, d = final_state
    grid[x][y] = direction_symbols[d]
    st.session_state.grid = grid

    st.markdown(f"### 🧮 현재 점수: {st.session_state.score}")
    st.markdown(f"### 🏆 최고 점수: {st.session_state.max_score}")
    st.markdown(f"### 📊 누적 점수: {st.session_state.total_score}")
    render_grid(grid)

    if success:
        st.success("🎯 목표 2개 모두 도달 성공!")
    else:
        st.info("🎯 모든 목표에 도달하지 못했습니다.")

    st.session_state.score_log.append({
        "레벨": level,
        "점수": st.session_state.score,
        "누적점수": st.session_state.total_score,
        "성공여부": "성공" if success else "실패",
        "시간(초)": round(elapsed, 2)
    })

# 점수 저장
if st.button("💾 점수 기록 저장"):
    df = pd.DataFrame(st.session_state.score_log)
    st.download_button(
        label="CSV 파일 다운로드",
        data=df.to_csv(index=False).encode('utf-8-sig'),
        file_name="robot_score_log.csv",
        mime='text/csv'
    )
