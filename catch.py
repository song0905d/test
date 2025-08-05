import streamlit as st
import random
import time
import pandas as pd

# 로봇 방향 표시
direction_symbols = ['↑', '→', '↓', '←']
dx = [-1, 0, 1, 0]  # 위, 오른쪽, 아래, 왼쪽
dy = [0, 1, 0, -1]

# 점수 테이블 초기화
if 'score_log' not in st.session_state:
    st.session_state.score_log = []

def create_map(level):
    size = 8
    grid = [['⬜' for _ in range(size)] for _ in range(size)]

    all_positions = [(i, j) for i in range(size) for j in range(size)]
    start_pos = random.choice(all_positions)
    all_positions.remove(start_pos)

    goal_pos = random.choice(all_positions)
    all_positions.remove(goal_pos)

    obstacle_counts = {1: 5, 2: 10, 3: 15}
    num_obstacles = obstacle_counts.get(level, 5)
    obstacle_pos = random.sample(all_positions, num_obstacles)

    start_dir = random.randint(0, 3) if level >= 2 else 0

    grid[start_pos[0]][start_pos[1]] = direction_symbols[start_dir]
    grid[goal_pos[0]][goal_pos[1]] = '🎯'
    for ox, oy in obstacle_pos:
        grid[ox][oy] = '🧱'

    return grid, start_pos, start_dir, goal_pos, set(obstacle_pos)

def render_grid(grid):
    for row in grid:
        st.markdown(''.join(row))

def move_robot(grid, pos, direction, commands, goal_pos, obstacles, level):
    x, y = pos
    size = len(grid)
    score = 0
    reached_goal = False
    for cmd in commands:
        grid[x][y] = '⬜'
        if cmd == '앞으로':
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
            if (x, y) == goal_pos:
                grid[x][y] = '✅'
                level_score = {1: 5, 2: 10, 3: 20}
                score += level_score.get(level, 5)
                reached_goal = True
                break
        grid[x][y] = direction_symbols[direction]
    return grid, reached_goal, score

# UI
st.title("🤖 로봇 명령어 퍼즐 게임 (시간 제한 & 점수 저장)")

level = st.selectbox("레벨을 선택하세요", [1, 2, 3], format_func=lambda x: f"Level {x}")

if 'grid' not in st.session_state:
    st.session_state.grid, st.session_state.pos, st.session_state.dir, st.session_state.goal, st.session_state.obstacles = create_map(level)
    st.session_state.score = 0
    st.session_state.max_score = 0
    st.session_state.total_score = 0

st.markdown(f"### 🧮 현재 점수: {st.session_state.score}")
st.markdown(f"### 🏆 최고 점수: {st.session_state.max_score}")
st.markdown(f"### 📊 누적 점수: {st.session_state.total_score}")

render_grid(st.session_state.grid)

commands_input = st.text_area("명령어 입력 (예: 앞으로, 오른쪽 회전, 왼쪽 회전, 집기)", height=150)
commands = [line.strip() for line in commands_input.strip().split('\n') if line.strip()]

# 명령 실행
if st.button("명령어 실행"):
    start_time = time.time()
    st.write("⏱ 명령 실행 중입니다... (12초 제한)")
    grid, success, delta_score = move_robot(
        st.session_state.grid,
        st.session_state.pos,
        st.session_state.dir,
        commands,
        st.session_state.goal,
        st.session_state.obstacles,
        level
    )
    elapsed = time.time() - start_time

    if elapsed > 12:
        st.error(f"⏰ 제한 시간 초과! ({elapsed:.2f}초)")
        delta_score = 0
        success = False
    else:
        st.success(f"✅ 명령어 처리 완료 ({elapsed:.2f}초)")

    st.session_state.score += delta_score
    st.session_state.total_score += delta_score
    if st.session_state.score > st.session_state.max_score:
        st.session_state.max_score = st.session_state.score

    st.session_state.grid = grid

    st.markdown(f"### 🧮 현재 점수: {st.session_state.score}")
    st.markdown(f"### 🏆 최고 점수: {st.session_state.max_score}")
    st.markdown(f"### 📊 누적 점수: {st.session_state.total_score}")

    render_grid(grid)

    if success:
        st.success("🎯 목표 도달 성공! 점수가 추가되었습니다.")
    else:
        st.info("목표에 도달하지 못했습니다.")

    # 점수 기록 저장
    st.session_state.score_log.append({
        "레벨": level,
        "점수": st.session_state.score,
        "누적점수": st.session_state.total_score,
        "성공여부": "성공" if success else "실패",
        "시간(초)": round(elapsed, 2)
    })

# 점수 저장 다운로드
if st.button("💾 점수 기록 저장"):
    df = pd.DataFrame(st.session_state.score_log)
    st.download_button(
        label="CSV 파일 다운로드",
        data=df.to_csv(index=False).encode('utf-8-sig'),
        file_name="robot_score_log.csv",
        mime='text/csv'
    )

# 다시 시작
if st.button("🔁 다시 시작"):
    st.session_state.grid, st.session_state.pos, st.session_state.dir, st.session_state.goal, st.session_state.obstacles = create_map(level)
    st.session_state.score = 0
    st.experimental_rerun()
