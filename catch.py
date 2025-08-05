import streamlit as st
import time
import random

# 페이지 설정
st.set_page_config(page_title="자동 테트리스", layout="centered")

# 보드 설정
ROWS, COLS = 20, 5
EMPTY = "⬛"
BLOCK = "🟥"

# 기본 블록 (2x2 정사각형)
BLOCK_SHAPE = [[1, 1],
                [1, 1]]

# 상태 초기화
if 'board' not in st.session_state:
    st.session_state.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
if 'block_pos' not in st.session_state:
    st.session_state.block_pos = [0, COLS // 2 - 1]  # 시작 위치
if 'block_active' not in st.session_state:
    st.session_state.block_active = True
if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()
if 'last_move_time' not in st.session_state:
    st.session_state.last_move_time = time.time()

# 블록 놓기 함수
def place_block():
    for i in range(2):
        for j in range(2):
            if BLOCK_SHAPE[i][j]:
                r = st.session_state.block_pos[0] + i
                c = st.session_state.block_pos[1] + j
                if 0 <= r < ROWS and 0 <= c < COLS:
                    st.session_state.board[r][c] = 1

# 블록 충돌 검사

def check_collision(dr, dc):
    for i in range(2):
        for j in range(2):
            if BLOCK_SHAPE[i][j]:
                r = st.session_state.block_pos[0] + i + dr
                c = st.session_state.block_pos[1] + j + dc
                if r >= ROWS or c < 0 or c >= COLS:
                    return True
                if r >= 0 and st.session_state.board[r][c]:
                    return True
    return False

# 블록 이동

def move_block(dr, dc):
    if not check_collision(dr, dc):
        st.session_state.block_pos[0] += dr
        st.session_state.block_pos[1] += dc
    elif dr == 1:
        # 아래로 못 움직이면 고정
        st.session_state.block_active = False
        place_block()

# 한 줄 완성 시 삭제

def clear_lines():
    new_board = [row for row in st.session_state.board if any(cell == 0 for cell in row)]
    cleared = ROWS - len(new_board)
    for _ in range(cleared):
        new_board.insert(0, [0] * COLS)
    st.session_state.board = new_board

# 블록 시각화용 복사 보드 만들기

def get_display_board():
    display = [row[:] for row in st.session_state.board]
    if st.session_state.block_active:
        for i in range(2):
            for j in range(2):
                if BLOCK_SHAPE[i][j]:
                    r = st.session_state.block_pos[0] + i
                    c = st.session_state.block_pos[1] + j
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        display[r][c] = 1
    return display

# 자동으로 아래로 이동
current_time = time.time()
elapsed_time = current_time - st.session_state.start_time
interval_decrease = int(elapsed_time // 5) * 0.15
move_interval = max(0.2, 2.0 - interval_decrease)

if st.session_state.block_active:
    if current_time - st.session_state.last_move_time >= move_interval:
        move_block(1, 0)
        st.session_state.last_move_time = current_time
else:
    clear_lines()
    st.session_state.block_pos = [0, COLS // 2 - 1]
    st.session_state.block_active = True
    st.session_state.last_move_time = current_time

# UI
st.title("🧱 자동 테트리스 (좌우 이동만 가능)")

col1, col2 = st.columns(2)
with col1:
    if st.button("⬅️"):
        move_block(0, -1)
with col2:
    if st.button("➡️"):
        move_block(0, 1)

# 보드 출력
board_display = get_display_board()
for row in board_display:
    st.markdown("".join([BLOCK if cell else EMPTY for cell in row]))

# 보드 출력
board_display = get_display_board()
for row in board_display:
    st.markdown("".join([BLOCK if cell else EMPTY for cell in row]))
