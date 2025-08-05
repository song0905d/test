import streamlit as st
import time
import random
import copy

# 페이지 설정
st.set_page_config(page_title="자동 테트리스", layout="wide")

# 보드 설정
ROWS, COLS = 11, 14  # 세로 5줄 늘림, 가로 넓게 유지
EMPTY = "⬛"
BLOCKS = {
    'O': [[1, 1], [1, 1]],
    'I': [[1], [1], [1], [1]],
    'L': [[1, 0], [1, 0], [1, 1]],
    'Z': [[1, 1, 0], [0, 1, 1]]
}
BLOCK_EMOJI = "🟥"

# 상태 초기화
if 'board' not in st.session_state:
    st.session_state.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
if 'block_pos' not in st.session_state:
    st.session_state.block_pos = [0, COLS // 2 - 1]
if 'block_active' not in st.session_state:
    st.session_state.block_active = True
if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()
if 'last_move_time' not in st.session_state:
    st.session_state.last_move_time = time.time()
if 'current_block' not in st.session_state:
    st.session_state.current_block = random.choice(list(BLOCKS.values()))
if 'game_over' not in st.session_state:
    st.session_state.game_over = False
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'high_score' not in st.session_state:
    st.session_state.high_score = 0
if 'tick' not in st.session_state:
    st.session_state.tick = time.time()

# 블록 회전 함수
def rotate_block(block):
    return [list(row) for row in zip(*block[::-1])]

# 블록 놓기 함수
def place_block():
    for i in range(len(st.session_state.current_block)):
        for j in range(len(st.session_state.current_block[0])):
            if st.session_state.current_block[i][j]:
                r = st.session_state.block_pos[0] + i
                c = st.session_state.block_pos[1] + j
                if 0 <= r < ROWS and 0 <= c < COLS:
                    st.session_state.board[r][c] = 1

# 블록 충돌 검사

def check_collision(dr, dc, block=None):
    block = block or st.session_state.current_block
    for i in range(len(block)):
        for j in range(len(block[0])):
            if block[i][j]:
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
        place_block()
        st.session_state.block_active = False

# 블록 회전 적용

def rotate_current_block():
    rotated = rotate_block(st.session_state.current_block)
    if not check_collision(0, 0, rotated):
        st.session_state.current_block = rotated

# 줄 삭제 및 점수 처리

def clear_lines():
    new_board = [row for row in st.session_state.board if any(cell == 0 for cell in row)]
    cleared = ROWS - len(new_board)
    for _ in range(cleared):
        new_board.insert(0, [0] * COLS)
    st.session_state.board = new_board
    st.session_state.score += cleared * 100
    if st.session_state.score > st.session_state.high_score:
        st.session_state.high_score = st.session_state.score

# 새 블록 생성 및 게임 오버 확인

def spawn_new_block():
    st.session_state.current_block = copy.deepcopy(random.choice(list(BLOCKS.values())))
    st.session_state.block_pos = [0, COLS // 2 - 1]
    st.session_state.block_active = True
    st.session_state.last_move_time = time.time()
    if check_collision(0, 0):
        st.session_state.game_over = True

# 보드 표시용 복사본

def get_display_board():
    display = [row[:] for row in st.session_state.board]
    if st.session_state.block_active:
        for i in range(len(st.session_state.current_block)):
            for j in range(len(st.session_state.current_block[0])):
                if st.session_state.current_block[i][j]:
                    r = st.session_state.block_pos[0] + i
                    c = st.session_state.block_pos[1] + j
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        display[r][c] = 1
    return display

# 자동 하강 처리 (가상 버튼 클릭처럼 구현)
current_time = time.time()
elapsed_time = current_time - st.session_state.start_time
interval_decrease = int(elapsed_time // 5) * 0.15
move_interval = max(0.3, 2.0 - interval_decrease)
level = 1 + int(elapsed_time // 10)

if not st.session_state.game_over:
    if current_time - st.session_state.tick > move_interval:
        if st.session_state.block_active:
            move_block(1, 0)
        else:
            clear_lines()
            spawn_new_block()
        st.session_state.tick = current_time

# UI 출력
st.title("🧱 자동 테트리스")

if st.session_state.game_over:
    st.error(f"💀 게임 오버! 최종 점수: {st.session_state.score}")
else:
    st.write(f"🏆 점수: {st.session_state.score} | 📈 최고 점수: {st.session_state.high_score} | 🎮 레벨: {level}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("⬅️"):
            move_block(0, -1)
    with col2:
        if st.button("⟳ 회전"):
            rotate_current_block()
    with col3:
        if st.button("➡️"):
            move_block(0, 1)
    with col4:
        if st.button("⬇️ 아래로"):
            move_block(1, 0)

# 보드 출력
board_display = get_display_board()
for row in board_display:
    st.markdown("".join([BLOCK_EMOJI if cell else EMPTY for cell in row]))
