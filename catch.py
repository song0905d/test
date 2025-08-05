import streamlit as st
import time
import random

# 페이지 설정
st.set_page_config(page_title="두더지 잡기 게임", layout="centered")

# 상태 초기화
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'high_score' not in st.session_state:
    st.session_state.high_score = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'game_over' not in st.session_state:
    st.session_state.game_over = False
if 'mole_position' not in st.session_state:
    st.session_state.mole_position = None

# 설정
GRID_SIZE = 3
GAME_DURATION = 45  # 게임 시간 (초)
START_DURATION = 1.1  # 시작 노출 시간
MIN_DURATION = 0.3    # 최소 노출 시간
INTERVAL_DECREASE = 0.11  # 5초마다 감소량

# 타이머 시작 함수
def start_game():
    st.session_state.score = 0
    st.session_state.start_time = time.time()
    st.session_state.game_over = False
    st.session_state.mole_position = None

# 노출 시간 계산 함수
def get_mole_duration():
    elapsed = time.time() - st.session_state.start_time
    dec = int(elapsed // 5) * INTERVAL_DECREASE
    return max(MIN_DURATION, START_DURATION - dec)

# 두더지 랜덤 위치 설정
def set_random_mole():
    st.session_state.mole_position = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

# 점수 증가 함수
def hit_mole(row, col):
    if not st.session_state.game_over and st.session_state.mole_position == (row, col):
        st.session_state.score += 1
        set_random_mole()

# UI 렌더링
st.title("🎯 두더지 잡기 게임")

if st.button("게임 시작 / 재시작"):
    start_game()
    set_random_mole()

# 게임 실행
if st.session_state.start_time:
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, int(GAME_DURATION - elapsed_time))
    st.write(f"⏱️ 남은 시간: {remaining_time}초")
    st.write(f"🏆 현재 점수: {st.session_state.score}")
    st.write(f"⭐ 최고 점수: {st.session_state.high_score}")

    if elapsed_time >= GAME_DURATION:
        st.session_state.game_over = True
        if st.session_state.score > st.session_state.high_score:
            st.session_state.high_score = st.session_state.score
        st.success("게임 종료! 다시 시작하려면 버튼을 누르세요.")
    else:
        duration = get_mole_duration()

        cols = st.columns(GRID_SIZE)
        for row in range(GRID_SIZE):
            with cols[row]:
                for col in range(GRID_SIZE):
                    if (row, col) == st.session_state.mole_position:
                        if st.button("🐹", key=f"{row}-{col}-{time.time()}"):
                            hit_mole(row, col)
        time.sleep(duration)
        set_random_mole()
