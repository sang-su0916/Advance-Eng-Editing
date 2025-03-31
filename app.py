import streamlit as st
import os
# OpenAI 모듈 임포트 수정
try:
    from openai import OpenAI
except ImportError:
    import openai
import pandas as pd
import numpy as np
import json
import hashlib
import csv
import io
import datetime
import altair as alt
import zipfile
from dotenv import load_dotenv
from problems import SAMPLE_PROBLEMS
from prompts import get_correction_prompt
import uuid
import re

# Load environment variables first
load_dotenv()

# Initialize API configurations
try:
    import google.generativeai as genai
    # 환경 변수 이름을 GOOGLE_API_KEY로 통일
    # 이전 버전 호환성을 위해 GEMINI_API_KEY도 체크
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_api_key:
        genai.configure(api_key=google_api_key)
except ImportError:
    st.error("google-generativeai 패키지가 설치되지 않았습니다. 'pip install google-generativeai'를 실행해주세요.")
except Exception as e:
    st.error(f"Gemini API 초기화 중 오류가 발생했습니다: {str(e)}")

# Initialize session state
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
if 'gemini_api_key' not in st.session_state:
    # 환경 변수 이름을 통일하되, 이전 버전 호환성 유지
    st.session_state.gemini_api_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")

# Page configuration
st.set_page_config(
    page_title="학원자동시스템관리",
    page_icon="🏫",
    layout="wide"
)

# Function to initialize session states
def initialize_session_states():
    """세션 상태 초기화"""
    if 'current_problem' not in st.session_state:
        st.session_state.current_problem = None
    if 'user_answer' not in st.session_state:
        st.session_state.user_answer = ""
    if 'feedback' not in st.session_state:
        st.session_state.feedback = None
    if 'input_method' not in st.session_state:
        st.session_state.input_method = "text"
    if 'custom_problems' not in st.session_state:
        st.session_state.custom_problems = {}
    if 'save_dir' not in st.session_state:
        st.session_state.save_dir = os.getcwd()
    if 'last_problem_key' not in st.session_state:
        st.session_state.last_problem_key = None
    if 'selected_level' not in st.session_state:
        st.session_state.selected_level = "초급"
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'users' not in st.session_state:
        st.session_state.users = {}
    if 'teacher_problems' not in st.session_state:
        st.session_state.teacher_problems = {}
    if 'student_records' not in st.session_state:
        st.session_state.student_records = {}
    
    # API 키 초기화 - .env 파일에서 로드
    load_dotenv()
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if 'gemini_api_key' not in st.session_state:
        # 환경 변수 이름을 통일하되, 이전 버전 호환성 유지
        st.session_state.gemini_api_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")

# Initialize session state
initialize_session_states()

# User management functions
def save_users_data():
    """사용자 데이터를 JSON 파일로 저장"""
    try:
        data = {
            'teacher_problems': st.session_state.teacher_problems,
            'student_records': st.session_state.student_records,
            'users': st.session_state.users if 'users' in st.session_state else {}
        }
        with open('users_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"데이터 저장 중 오류 발생: {str(e)}")
        return False

def load_users_data():
    """JSON 파일에서 사용자 데이터 로드"""
    try:
        if os.path.exists('users_data.json'):
            with open('users_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.teacher_problems = data.get('teacher_problems', {})
                st.session_state.student_records = data.get('student_records', {})
                st.session_state.users = data.get('users', {})
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {str(e)}")

# Load user data at app start
load_users_data()

def hash_password(password):
    """비밀번호 해싱 함수"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    """사용자 로그인 처리"""
    try:
        if username in st.session_state.users:
            hashed_password = hash_password(password)
            if st.session_state.users[username]["password"] == hashed_password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_role = st.session_state.users[username]["role"]
                
                # API 키 다시 로드
                load_dotenv()
                st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
                st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
                
                return True
            else:
                st.error("비밀번호가 일치하지 않습니다.")
        else:
            st.error("존재하지 않는 사용자입니다.")
        return False
    except Exception as e:
        st.error(f"로그인 처리 중 오류가 발생했습니다: {e}")
        return False

def logout_user():
    """사용자 로그아웃 처리"""
    # API 키는 유지하지 않음
    st.session_state.clear()
    
    # 기본 상태 설정
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_role = None
    
    # API 키 재로드
    load_dotenv()
    st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

def register_user(username, password, role, name, email, created_by=None):
    """새 사용자 등록"""
    if username in st.session_state.users:
        return False, "이미 존재하는 사용자 이름입니다."
    
    hashed_password = hash_password(password)
    st.session_state.users[username] = {
        "password": hashed_password,
        "role": role,
        "name": name,
        "email": email,
        "created_by": created_by,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    # 학생인 경우 학생 기록 초기화
    if role == "student":
        st.session_state.student_records[username] = {
            "solved_problems": [],
            "total_problems": 0,
            "feedback_history": []
        }
    
    save_users_data()
    return True, "사용자가 성공적으로 등록되었습니다."

# Login page
def login_page():
    # 배경 이미지와 스타일 적용
    st.markdown("""
    <style>
    .main-container {
        background-color: #f5f7f9;
        border-radius: 10px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        max-width: 600px;
        margin: 2rem auto;
    }
    
    .title-container {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .title-container h1 {
        color: #1e3a8a;
        font-weight: 700;
    }
    
    .login-form {
        padding: 1.5rem;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .input-group {
        margin-bottom: 1.2rem;
    }
    
    .login-btn {
        background-color: #1e88e5;
        color: white;
        width: 100%;
        padding: 0.5rem 0;
        border-radius: 5px;
        border: none;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    
    .login-btn:hover {
        background-color: #1565c0;
    }
    
    .info-container {
        margin-top: 1.5rem;
        padding: 1rem;
        background-color: #e3f2fd;
        border-radius: 8px;
        font-size: 0.9rem;
    }
    
    .banner {
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(45deg, #1e88e5, #1e3a8a);
        color: white;
        border-radius: 8px;
    }
    
    .banner h2 {
        margin: 0;
        font-weight: 600;
    }
    </style>
    
    <div class="main-container">
        <div class="banner">
            <h2>영어 학습 관리 시스템</h2>
            <p>AI 기반 맞춤형 영어 학습 및 첨삭 서비스</p>
        </div>
        <div class="title-container">
            <h1>로그인</h1>
        </div>
        <div class="login-form">
    """, unsafe_allow_html=True)
    
    # 로그인 폼
    username = st.text_input("아이디", key="login_username", placeholder="아이디를 입력하세요")
    password = st.text_input("비밀번호", type="password", key="login_password", placeholder="비밀번호를 입력하세요")
    
    login_button = st.button("로그인", key="login_btn", use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)  # login-form div 닫기
    
    # 역할별 안내 정보
    with st.expander("역할별 안내", expanded=False):
        st.info("""
        ### 학생
        - 문제 풀기 및 학습 기록 확인
        - AI 첨삭 받기
        - 개인별 맞춤형 학습 관리
        
        ### 교사
        - 문제 출제 및 관리
        - 학생 등록 및 관리
        - 학생 답변 채점 및 첨삭
        - 학습 진도 관리 및 분석
        
        ### 관리자
        - 시스템 전체 관리
        - API 키 설정
        - 데이터 백업 및 복원
        """)
    
    st.markdown("</div>", unsafe_allow_html=True)  # main-container div 닫기
    
    # 로그인 처리
    if login_button:
        if login_user(username, password):
            st.success("로그인 성공!")
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    
    # 데모 계정 정보 - 숨김 형태로 표시
    with st.expander("데모 계정 정보", expanded=False):
        st.markdown("""
        ### 데모 계정
        > 시스템을 체험해볼 수 있는 데모 계정입니다.
        
        **학생:**
        - 아이디: student
        - 비밀번호: student123
        
        **교사:**
        - 아이디: teacher
        - 비밀번호: teacher123
        
        **관리자:**
        - 아이디: admin
        - 비밀번호: admin123
        """)

# Student Dashboard
def student_dashboard():
    st.title(f"학생 대시보드 - {st.session_state.users[st.session_state.username]['name']}님")
    
    # 사이드바 - 학생 메뉴
    st.sidebar.title("학생 메뉴")
    
    menu = st.sidebar.radio(
        "메뉴 선택:",
        ["문제 풀기", "내 학습 기록", "프로필"]
    )
    
    if menu == "문제 풀기":
        student_solve_problems()
    elif menu == "내 학습 기록":
        student_learning_history()
    elif menu == "프로필":
        student_profile()
    
    # 로그아웃 버튼
    logout_button = st.sidebar.button("로그아웃")
    if logout_button:
        logout_user()
        st.rerun()

def student_solve_problems():
    st.header("문제 풀기")
    
    # 모든 저장된 문제 수 확인
    total_problems = len(st.session_state.teacher_problems)
    
    if total_problems == 0:
        st.info("아직 등록된 문제가 없습니다. 선생님께 문의해주세요.")
        return
        
    # 문제 풀기 옵션
    options_tab, random_tab = st.tabs(["문제 선택", "랜덤 문제 풀이"])
    
    with options_tab:
        # 문제 필터링 옵션
        col1, col2, col3 = st.columns(3)
        
        with col1:
            categories = list(set(p.get("category", "기타") for p in st.session_state.teacher_problems.values()))
            selected_category = st.selectbox("카테고리 선택:", ["전체"] + categories, key="category_select")
        
        with col2:
            difficulty_levels = list(set(p.get("difficulty", "미지정") for p in st.session_state.teacher_problems.values()))
            selected_difficulty = st.selectbox("난이도 선택:", ["전체"] + difficulty_levels, key="difficulty_select")
            
        with col3:
            topics = list(set(p.get("topic", "기타") for p in st.session_state.teacher_problems.values()))
            selected_topic = st.selectbox("주제 선택:", ["전체"] + topics, key="topic_select")
        
        # 필터링된 문제 목록
        filtered_problems = st.session_state.teacher_problems.copy()
        
        if selected_category != "전체":
            filtered_problems = {k: v for k, v in filtered_problems.items() if v.get("category") == selected_category}
            
        if selected_difficulty != "전체":
            filtered_problems = {k: v for k, v in filtered_problems.items() if v.get("difficulty") == selected_difficulty}
            
        if selected_topic != "전체":
            filtered_problems = {k: v for k, v in filtered_problems.items() if v.get("topic") == selected_topic}
        
        if not filtered_problems:
            st.info("선택한 필터에 맞는 문제가 없습니다.")
            return
        
        # 문제 수와 시간 설정
        col1, col2 = st.columns(2)
        with col1:
            available_count = len(filtered_problems)
            max_count = min(available_count, 20)  # 최대 20개까지만 선택 가능
            
            num_options = [5, 10, 15, 20]
            valid_options = [n for n in num_options if n <= max_count]
            if not valid_options:
                valid_options = [max_count]
                
            num_problems = st.selectbox(
                f"풀 문제 수 (총 {available_count}개 중):", 
                valid_options,
                index=min(1, len(valid_options)-1)  # 기본값은 10개 또는 가능한 최대값
            )
        
        with col2:
            time_limit = st.selectbox("제한 시간 (분):", [10, 20, 30, 40, 60], index=1)
        
        # 선택된 필터에서 문제 목록 가져오기
        problem_keys = list(filtered_problems.keys())
        
        # 문제 수가 선택한 수보다 많으면 랜덤하게 선택
        if len(problem_keys) > num_problems:
            import random
            problem_keys = random.sample(problem_keys, num_problems)
        
        st.write(f"**선택된 필터에서 {len(problem_keys)}개 문제**를 풀이합니다.")
        
        if st.button("문제 풀기 시작", key="start_selected_problems"):
            # 세션 상태에 선택된 문제와 시간 제한 저장
            st.session_state.selected_problems = [(key, filtered_problems[key]) for key in problem_keys]
            st.session_state.time_limit_minutes = time_limit
            st.session_state.current_problem_index = 0
            st.session_state.start_time = datetime.datetime.now()
            st.session_state.answers = []
            st.session_state.solving_mode = True
            st.rerun()
    
    with random_tab:
        # 완전 랜덤으로 문제를 선택하는 방식
        st.write("모든 문제에서 랜덤으로 선택합니다.")
        
        # 문제 수와 시간 설정
        col1, col2 = st.columns(2)
        with col1:
            num_random_problems = st.selectbox(
                f"풀 문제 수 (총 {total_problems}개 중):", 
                [5, 10, 15, 20],
                index=1,
                key="random_num"
            )
        with col2:
            random_time_limit = st.selectbox("제한 시간 (분):", [10, 20, 30, 40, 60], index=1, key="random_time")
        
        if st.button("랜덤 문제 풀기 시작", key="start_random_problems"):
            import random
            # 모든 문제에서 랜덤으로 선택
            problem_items = list(st.session_state.teacher_problems.items())
            if len(problem_items) > num_random_problems:
                selected_items = random.sample(problem_items, num_random_problems)
            else:
                selected_items = problem_items
            
            # 세션 상태에 선택된 문제와 시간 제한 저장
            st.session_state.selected_problems = selected_items
            st.session_state.time_limit_minutes = random_time_limit
            st.session_state.current_problem_index = 0
            st.session_state.start_time = datetime.datetime.now()
            st.session_state.answers = []
            st.session_state.solving_mode = True
            st.rerun()
    
    # 문제 풀이 모드인 경우 문제 표시
    if st.session_state.get('solving_mode', False):
        solve_problem_sequence()

# 문제 풀이 순서 및 모드 처리
def solve_problem_sequence():
    # 필요한 세션 상태 변수가 초기화되었는지 확인
    if 'selected_problems' not in st.session_state:
        st.error("문제 데이터가 없습니다. 다시 시도해주세요.")
        st.session_state.solving_mode = False
        return
    
    if 'answers' not in st.session_state:
        st.session_state.answers = []
    
    # 시간 제한 설정
    start_time = st.session_state.start_time
    time_limit = st.session_state.time_limit_minutes
    
    # 현재 문제 인덱스
    current_index = st.session_state.current_problem_index
    total_problems = len(st.session_state.selected_problems)
    
    # 시간 계산
    elapsed_time = datetime.datetime.now() - start_time
    remaining_seconds = max(0, time_limit * 60 - elapsed_time.total_seconds())
    
    # 시간 표시
    minutes, seconds = divmod(int(remaining_seconds), 60)
    
    # 진행 상태 정보 표시
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f"##### 문제 {current_index + 1}/{total_problems}")
    
    with col2:
        progress = (current_index) / total_problems
        st.progress(progress)
    
    with col3:
        timer_color = "green"
        if remaining_seconds < 300:  # 5분 미만
            timer_color = "orange"
        if remaining_seconds < 60:   # 1분 미만
            timer_color = "red"
        
        st.markdown(f"##### 남은 시간: <span style='color:{timer_color};'>{minutes:02d}:{seconds:02d}</span>", unsafe_allow_html=True)
    
    # 시간이 다 되면 결과 페이지로 이동
    if remaining_seconds <= 0:
        st.warning("시간이 종료되었습니다. 결과를 확인하세요.")
        
        # 남은 문제들을 빈 답변으로 채우기
        while len(st.session_state.answers) < total_problems:
            st.session_state.answers.append("")
        
        display_results()
        return
    
    # 5개 문제씩 보여주기 위한 페이지 계산
    problems_per_page = 5
    current_page = current_index // problems_per_page
    page_start = current_page * problems_per_page
    page_end = min(page_start + problems_per_page, total_problems)
    
    # 현재 페이지의 문제 목록 (탭으로 표시)
    problem_tabs = st.tabs([f"문제 {i+1}" for i in range(page_start, page_end)])
    
    for i, tab in enumerate(problem_tabs):
        tab_index = page_start + i
        
        # 범위를 넘어가면 건너뛰기
        if tab_index >= total_problems:
            continue
        
        with tab:
            # 현재 문제 정보
            problem_id, problem_data = st.session_state.selected_problems[tab_index]
            
            # 현재 문제 인덱스 업데이트 (탭 클릭 시)
            if i != (current_index % problems_per_page):
                st.session_state.current_problem_index = tab_index
            
            # 문제 표시
            display_and_solve_problem(problem_id, problem_data, tab_index)
    
    # 이전/다음 페이지 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_page > 0:
            if st.button("⬅️ 이전 세트", key="prev_page"):
                st.session_state.current_problem_index = page_start - 1
                st.rerun()
    
    with col3:
        if page_end < total_problems:
            if st.button("다음 세트 ➡️", key="next_page"):
                st.session_state.current_problem_index = page_end
                st.rerun()
    
    # 제출 버튼
    if st.button("모든 문제 제출", key="submit_all", type="primary"):
        # 미답변 문제가 있는지 확인
        if len(st.session_state.answers) < total_problems:
            missing_count = total_problems - len(st.session_state.answers)
            if st.warning(f"아직 {missing_count}개의 문제에 답변하지 않았습니다. 제출하시겠습니까?"):
                # 남은 문제들을 빈 답변으로 채우기
                while len(st.session_state.answers) < total_problems:
                    st.session_state.answers.append("")
        
        display_results()
    

def display_and_solve_problem(problem_id, problem_data, index):
    """문제를 표시하고 학생이 풀 수 있도록 함"""
    # 문제 정보 표시
    st.markdown(f"### {problem_data['question']}")
    
    if 'context' in problem_data and problem_data['context']:
        st.markdown(f"**상황**: {problem_data['context']}")
    
    # 문제 유형에 따라 다른 입력 방식 제공
    question_type = problem_data.get('question_type', '객관식')
    
    if question_type == '객관식':
        # 객관식 처리
        options = problem_data.get('options', '')
        if options:
            # 옵션 파싱
            option_list = []
            # A. Option B. Option 형식 또는 여러 줄로 된 옵션 처리
            for line in options.split('\n'):
                line = line.strip()
                if line:
                    option_list.append(line)
            
            # 한 줄로 된 "A. Option B. Option" 형식 처리
            if len(option_list) == 1 and len(option_list[0]) > 3:
                import re
                parts = re.split(r'([A-Z]\.\s+)', option_list[0])
                new_options = []
                for i in range(1, len(parts), 2):
                    if i+1 < len(parts):
                        new_options.append(parts[i] + parts[i+1].strip())
                if new_options:
                    option_list = new_options
            
            # 라디오 버튼으로 표시
            if option_list:
                # 이미 답변했는지 확인
                default_index = -1
                if index < len(st.session_state.answers):
                    answer = st.session_state.answers[index]
                    if answer in ['A', 'B', 'C', 'D', 'E']:
                        default_index = ord(answer) - ord('A')
                
                answer_options = []
                answer_labels = []
                
                for opt in option_list:
                    if len(opt) >= 2 and opt[0].isalpha() and opt[1] == '.':
                        label = opt[0]
                        text = opt[2:].strip()
                        answer_options.append(label)
                        answer_labels.append(f"{label}. {text}")
                    else:
                        answer_options.append(opt)
                        answer_labels.append(opt)
                
                selected = st.radio(
                    "답을 선택하세요:", 
                    range(len(answer_labels)),
                    format_func=lambda x: answer_labels[x],
                    index=default_index if default_index >= 0 and default_index < len(answer_labels) else 0,
                    key=f"radio_{problem_id}_{index}"
                )
                
                # 세션에 답변 저장
                while len(st.session_state.answers) <= index:
                    st.session_state.answers.append("")
                
                st.session_state.answers[index] = answer_options[selected][0] if len(answer_options[selected]) > 0 else ""
            else:
                # 옵션이 없는 경우 텍스트 입력 필드 제공
                answer = st.text_input(
                    "답을 입력하세요:",
                    value=st.session_state.answers[index] if index < len(st.session_state.answers) else "",
                    key=f"text_{problem_id}_{index}"
                )
                
                # 세션에 답변 저장
                while len(st.session_state.answers) <= index:
                    st.session_state.answers.append("")
                
                st.session_state.answers[index] = answer
        else:
            # 옵션이 없는 경우 텍스트 입력 필드 제공
            answer = st.text_input(
                "답을 입력하세요:",
                value=st.session_state.answers[index] if index < len(st.session_state.answers) else "",
                key=f"text_{problem_id}_{index}"
            )
            
            # 세션에 답변 저장
            while len(st.session_state.answers) <= index:
                st.session_state.answers.append("")
            
            st.session_state.answers[index] = answer
    
    elif question_type in ['주관식', '서술형']:
        # 주관식 또는 서술형 처리
        input_height = 100 if question_type == '서술형' else 50
        
        answer = st.text_area(
            "답을 입력하세요:",
            value=st.session_state.answers[index] if index < len(st.session_state.answers) else "",
            height=input_height,
            key=f"area_{problem_id}_{index}"
        )
        
        # 세션에 답변 저장
        while len(st.session_state.answers) <= index:
            st.session_state.answers.append("")
        
        st.session_state.answers[index] = answer
    
    else:
        # 기타 유형
        answer = st.text_area(
            "답을 입력하세요:",
            value=st.session_state.answers[index] if index < len(st.session_state.answers) else "",
            key=f"default_{problem_id}_{index}"
        )
        
        # 세션에 답변 저장
        while len(st.session_state.answers) <= index:
            st.session_state.answers.append("")
        
        st.session_state.answers[index] = answer
    
    # 다음 문제 버튼
    if index < len(st.session_state.selected_problems) - 1:
        if st.button("다음 문제 👉", key=f"next_{problem_id}"):
            st.session_state.current_problem_index = index + 1
            st.rerun()
    

def display_results():
    """문제 풀이 결과를 표시"""
    st.header("문제 풀이 결과")
    
    if not hasattr(st.session_state, 'selected_problems') or not hasattr(st.session_state, 'answers'):
        st.error("문제 풀이 데이터가 없습니다.")
        return
    
    total_problems = len(st.session_state.selected_problems)
    answered_problems = len([a for a in st.session_state.answers if a])
    
    st.write(f"총 {total_problems}개 문제 중 {answered_problems}개 문제에 답변하셨습니다.")
    
    # 제한 시간 정보
    start_time = st.session_state.start_time
    time_limit = st.session_state.time_limit_minutes
    elapsed_time = datetime.datetime.now() - start_time
    elapsed_minutes, elapsed_seconds = divmod(int(elapsed_time.total_seconds()), 60)
    
    st.write(f"소요 시간: {elapsed_minutes}분 {elapsed_seconds}초 (제한 시간: {time_limit}분)")
    
    # 각 문제에 대한 결과 표시
    with st.expander("문제별 답변 확인", expanded=True):
        for i, (problem_id, problem_data) in enumerate(st.session_state.selected_problems):
            st.markdown(f"### 문제 {i+1}")
            st.markdown(f"**{problem_data['question']}**")
            
            # 사용자 답변
            user_answer = st.session_state.answers[i] if i < len(st.session_state.answers) else ""
            st.markdown(f"**내 답변**: {user_answer if user_answer else '(답변 없음)'}")
            
            # 정답 표시
            correct_answer = problem_data.get('answer', '')
            st.markdown(f"**정답**: {correct_answer}")
            
            # 해설 표시
            if 'explanation' in problem_data and problem_data['explanation']:
                st.markdown(f"**해설**: {problem_data['explanation']}")
            
            # 피드백 생성 버튼
            if user_answer:  # 답변이 있는 경우에만 피드백 생성 버튼 표시
                if st.button(f"AI 피드백 받기", key=f"feedback_{i}"):
                    with st.spinner("AI가 피드백을 생성 중입니다..."):
                        feedback = generate_feedback(problem_data, user_answer)
                        st.session_state[f'feedback_{i}'] = feedback
            
            # 생성된 피드백 표시
            if f'feedback_{i}' in st.session_state:
                st.markdown("**AI 피드백:**")
                st.markdown(st.session_state[f'feedback_{i}'])
            
            st.markdown("---")
    
    # 학습 기록 저장
    if st.button("학습 기록 저장하기", key="save_record"):
        success = save_learning_record(
            st.session_state.selected_problems,
            st.session_state.answers,
            elapsed_time.total_seconds()
        )
        
        if success:
            st.success("학습 기록이 저장되었습니다.")
            # 풀이 모드 종료
            st.session_state.solving_mode = False
            
            # 다른 문제 풀기 버튼
            if st.button("다른 문제 풀기", key="solve_more"):
                # 상태 초기화
                if 'selected_problems' in st.session_state:
                    del st.session_state.selected_problems
                if 'answers' in st.session_state:
                    del st.session_state.answers
                if 'start_time' in st.session_state:
                    del st.session_state.start_time
                if 'current_problem_index' in st.session_state:
                    del st.session_state.current_problem_index
                
                st.rerun()
        else:
            st.error("학습 기록 저장에 실패했습니다.")
    else:
        # 취소 버튼
        if st.button("취소하고 돌아가기", key="cancel"):
            # 풀이 모드 종료 및 상태 초기화
            st.session_state.solving_mode = False
            if 'selected_problems' in st.session_state:
                del st.session_state.selected_problems
            if 'answers' in st.session_state:
                del st.session_state.answers
            if 'start_time' in st.session_state:
                del st.session_state.start_time
            if 'current_problem_index' in st.session_state:
                del st.session_state.current_problem_index
            
            st.rerun()


def generate_feedback(problem_data, user_answer):
    """AI를 사용하여 학생의 답변에 대한 첨삭을 생성하는 함수"""
    try:
        correct_answer = problem_data.get('answer', '')
        question = problem_data.get('question', '')
        
        # OpenAI API 사용 시도
        if 'openai_api_key' in st.session_state and st.session_state.openai_api_key:
            client = openai.OpenAI(api_key=st.session_state.openai_api_key)
            
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "너는 영어 교육 전문가로서 학생들의 답변을 평가하고 첨삭해주는 역할을 합니다."},
                        {"role": "user", "content": f"""
                        다음 문제에 대한 학생의 답변을 평가해주세요:
                        
                        문제: {question}
                        정답: {correct_answer}
                        학생 답변: {user_answer}
                        
                        다음 형식으로 답변해주세요:
                        1. 정확도 평가: 학생의 답변이 얼마나 정확한지 백분율로 표시
                        2. 강점: 학생 답변의 강점
                        3. 개선점: 학생 답변에서 개선이 필요한 부분
                        4. 조언: 더 나은 답변을 위한 조언
                        """}
                    ],
                    temperature=0.7
                )
                
                return response.choices[0].message.content
            except Exception as e:
                return f"OpenAI API 오류: {str(e)}\n\n간단한 평가: {'정답과 유사합니다.' if user_answer.lower() in correct_answer.lower() or correct_answer.lower() in user_answer.lower() else '정답과 차이가 있습니다.'}"
        
        # Google Gemini 모델 사용
        elif 'gemini_api_key' in st.session_state and st.session_state.gemini_api_key:
            try:
                genai.configure(api_key=st.session_state.gemini_api_key)
                
                # 사용 가능한 모델 목록 확인
                available_models = []
                try:
                    available_models = [m.name for m in genai.list_models()]
                except Exception as e:
                    return f"Gemini API 모델 목록 조회 오류: {str(e)}\n\n간단한 평가: {'정답과 유사합니다.' if user_answer.lower() in correct_answer.lower() or correct_answer.lower() in user_answer.lower() else '정답과 차이가 있습니다.'}"
                
                # 최신 모델 선택 (우선순위)
                preferred_models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
                model_name = None
                
                # 선호 모델 중에서 사용 가능한 것이 있는지 확인
                for preferred in preferred_models:
                    matches = [m for m in available_models if preferred in m]
                    if matches:
                        model_name = matches[0]
                        break
                
                # 기존 모델명으로 체크 (하위 호환성 유지)
                if not model_name:
                    if 'gemini-pro' in available_models:
                        model_name = 'gemini-pro'
                    elif 'models/gemini-pro' in available_models:
                        model_name = 'models/gemini-pro'
                    elif any('gemini' in m.lower() for m in available_models):
                        # gemini가 포함된 이름 중 첫 번째 모델 사용
                        model_name = next(m for m in available_models if 'gemini' in m.lower())
                
                if not model_name:
                    return f"사용 가능한 Gemini 모델이 없습니다. 사용 가능한 모델: {', '.join(available_models[:5])}...\n\n간단한 평가: {'정답과 유사합니다.' if user_answer.lower() in correct_answer.lower() or correct_answer.lower() in user_answer.lower() else '정답과 차이가 있습니다.'}"
                
                # 생성 설정 구성
                generation_config = {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
                
                # 모델 생성
                model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
                
                # 프롬프트 구성
                prompt = f"""
                이 문제에 대한 학생의 답안을 평가해주세요:
                
                문제: {question}
                정답: {correct_answer}
                학생 답안: {user_answer}
                
                다음 형식으로 답변해주세요:
                1. 정확도 평가: 학생의 답안이 얼마나 정확한지 백분율로 표시
                2. 강점: 학생 답안의 강점
                3. 개선점: 학생 답안에서 개선이 필요한 부분
                4. 조언: 더 나은 답변을 위한 조언
                """
                
                try:
                    response = model.generate_content(prompt)
                    feedback = response.text
                    return feedback
                except Exception as e:
                    return f"Gemini API 오류: {str(e)}\n\n간단한 평가: {'정답과 유사합니다.' if user_answer.lower() in correct_answer.lower() or correct_answer.lower() in user_answer.lower() else '정답과 차이가 있습니다.'}"
            except Exception as e:
                return f"Gemini API 처리 중 오류가 발생했습니다: {str(e)}"
        
        else:
            # API 키가 없는 경우 간단한 분석
            is_similar = user_answer.lower() in correct_answer.lower() or correct_answer.lower() in user_answer.lower()
            
            if is_similar:
                return "API 키가 설정되지 않아 상세 분석은 불가능합니다. 학생의 답변이 정답과 유사합니다. 좋은 답변입니다!"
            else:
                return "API 키가 설정되지 않아 상세 분석은 불가능합니다. 학생의 답변이 정답과 차이가 있습니다. 정답을 참고하세요."
    
    except Exception as e:
        return f"피드백 생성 중 오류가 발생했습니다: {str(e)}"

def student_learning_history():
    st.header("내 학습 기록")
    
    # 로그인한 학생의 기록 가져오기
    username = st.session_state.username
    if username not in st.session_state.student_records:
        st.info("아직 학습 기록이 없습니다. 문제를 풀어보세요!")
        return
    
    student_data = st.session_state.student_records[username]
    
    # 학습 통계 표시
    st.subheader("학습 통계")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 학습 문제 수", student_data["total_problems"])
    
    with col2:
        # 이번 주에 푼 문제 수
        week_problems = 0
        today = datetime.datetime.now()
        week_start = today - datetime.timedelta(days=today.weekday())
        
        for problem in student_data["solved_problems"]:
            try:
                problem_time = datetime.datetime.fromisoformat(problem["timestamp"])
                if problem_time >= week_start:
                    week_problems += 1
            except:
                pass
        
        st.metric("이번 주 학습 수", week_problems)
    
    with col3:
        # 오늘 푼 문제 수
        today_problems = 0
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for problem in student_data["solved_problems"]:
            try:
                problem_time = datetime.datetime.fromisoformat(problem["timestamp"])
                if problem_time >= today_start:
                    today_problems += 1
            except:
                pass
        
        st.metric("오늘 학습 수", today_problems)
    
    # 카테고리별 문제 분포
    if student_data["solved_problems"]:
        st.subheader("카테고리별 학습 분포")
        
        # 카테고리별 문제 수 계산
        categories = {}
        for problem in student_data["solved_problems"]:
            category = problem["problem"].get("category", "기타")
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1
        
        # 데이터프레임 생성
        df = pd.DataFrame({
            "카테고리": list(categories.keys()),
            "문제 수": list(categories.values())
        })
        
        # 차트 생성
        chart = alt.Chart(df).mark_bar().encode(
            x="문제 수:Q",
            y=alt.Y("카테고리:N", sort="-x"),
            color=alt.Color("카테고리:N", legend=None),
            tooltip=["카테고리", "문제 수"]
        ).properties(
            title="카테고리별 학습 분포"
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    # 최근 학습 기록
    st.subheader("최근 학습 기록")
    
    if not student_data["solved_problems"]:
        st.info("아직 학습 기록이 없습니다.")
    else:
        # 최근 5개 기록 표시
        recent_problems = sorted(
            student_data["solved_problems"], 
            key=lambda x: x["timestamp"] if "timestamp" in x else "", 
            reverse=True
        )[:5]
        
        for i, problem in enumerate(recent_problems):
            try:
                with st.expander(f"{i+1}. {problem['problem']['question'][:50]}... ({datetime.datetime.fromisoformat(problem['timestamp']).strftime('%Y-%m-%d %H:%M')})"):
                    st.subheader("문제")
                    st.write(problem["problem"]["question"])
                    
                    st.subheader("나의 답변")
                    st.write(problem["answer"])
                    
                    st.subheader("AI 첨삭")
                    st.markdown(problem["feedback"])
            except:
                st.error(f"기록 {i+1}을 표시하는 데 문제가 발생했습니다.")

def student_profile():
    st.header("내 프로필")
    
    username = st.session_state.username
    user_data = st.session_state.users[username]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("기본 정보")
        st.write(f"**이름:** {user_data['name']}")
        st.write(f"**이메일:** {user_data['email']}")
        st.write(f"**사용자 유형:** 학생")
        
        if "created_at" in user_data:
            try:
                created_at = datetime.datetime.fromisoformat(user_data["created_at"])
                st.write(f"**가입일:** {created_at.strftime('%Y-%m-%d')}")
            except:
                st.write(f"**가입일:** {user_data['created_at']}")
        
        if "created_by" in user_data and user_data["created_by"]:
            st.write(f"**등록한 교사:** {user_data['created_by']}")
    
    with col2:
        st.subheader("비밀번호 변경")
        
        current_password = st.text_input("현재 비밀번호", type="password")
        new_password = st.text_input("새 비밀번호", type="password")
        confirm_password = st.text_input("새 비밀번호 확인", type="password")
        
        if st.button("비밀번호 변경"):
            if not current_password or not new_password or not confirm_password:
                st.error("모든 필드를 입력해주세요.")
            elif hash_password(current_password) != user_data["password"]:
                st.error("현재 비밀번호가 올바르지 않습니다.")
            elif new_password != confirm_password:
                st.error("새 비밀번호와 확인이 일치하지 않습니다.")
            elif len(new_password) < 6:
                st.error("비밀번호는 최소 6자 이상이어야 합니다.")
            else:
                st.session_state.users[username]["password"] = hash_password(new_password)
                save_users_data()
                st.success("비밀번호가 성공적으로 변경되었습니다.")

# Teacher Dashboard
def teacher_dashboard():
    st.title(f"교사 대시보드 - {st.session_state.users[st.session_state.username]['name']}님")
    
    # 사이드바 - 교사 메뉴
    st.sidebar.title("교사 메뉴")
    
    menu = st.sidebar.radio(
        "메뉴 선택:",
        ["문제 관리", "학생 관리", "채점 및 첨삭", "프로필"]
    )
    
    if menu == "문제 관리":
        teacher_problem_management()
    elif menu == "학생 관리":
        teacher_student_management()
    elif menu == "채점 및 첨삭":
        teacher_grading()
    elif menu == "프로필":
        teacher_profile()
    
    # 로그아웃 버튼
    logout_button = st.sidebar.button("로그아웃")
    if logout_button:
        logout_user()
        st.rerun()

def check_api_key():
    """API 키가 설정되어 있는지 확인하는 함수"""
    # 사용자가 선택한 AI 모델에 따라 키 체크
    selected_model = st.session_state.get('selected_model', "OpenAI GPT")  # 기본값 OpenAI
    
    if selected_model == "OpenAI GPT":
        return bool(st.session_state.get('openai_api_key', '').strip())
    elif selected_model == "Google Gemini":
        return bool(st.session_state.get('gemini_api_key', '').strip())
    else:
        # 둘 중 하나라도 설정되어 있으면 True
        return bool(st.session_state.get('openai_api_key', '').strip() or 
                   st.session_state.get('gemini_api_key', '').strip())

def save_generated_problems(problems, school_type, grade, topic, difficulty):
    """생성된 문제를 저장하는 함수"""
    try:
        # 문제 내용을 파싱하여 개별 문제로 분리
        problem_list = parse_problems(problems)
        
        if not problem_list:
            return False, "문제 형식을 파싱할 수 없습니다. 형식을 확인해주세요."
        
        # 현재 로그인한 교사 정보
        teacher_username = st.session_state.username
        
        # 각 문제 저장
        for problem in problem_list:
            # 기본 정보 추가
            problem["school_type"] = school_type
            problem["grade"] = grade
            problem["topic"] = topic
            problem["difficulty"] = difficulty
            problem["created_by"] = teacher_username
            problem["created_at"] = datetime.datetime.now().isoformat()
            
            # 문제 ID 생성
            problem_id = str(uuid.uuid4())
            
            # 문제 저장
            st.session_state.teacher_problems[problem_id] = problem
        
        # 데이터 저장
        save_users_data()
        
        return True, f"{len(problem_list)}개의 문제가 성공적으로 저장되었습니다."
    
    except Exception as e:
        return False, f"문제 저장 중 오류가 발생했습니다: {str(e)}"

def generate_ai_problems():
    """AI를 활용하여 영어 문제 생성"""
    st.header("AI 문제 생성")
    
    # 상태 변수 선언
    if 'generated_problems' not in st.session_state:
        st.session_state.generated_problems = None
    
    # 학교 타입, 학년, 주제, 난이도 입력
    col1, col2 = st.columns(2)
    
    with col1:
        school_type = st.selectbox(
            "학교 유형:",
            ["초등학교", "중학교", "고등학교"],
            key="ai_school_type"
        )
        
        grade_options = {
            "초등학교": ["3학년", "4학년", "5학년", "6학년"],
            "중학교": ["1학년", "2학년", "3학년"],
            "고등학교": ["1학년", "2학년", "3학년"]
        }
        
        grade = st.selectbox(
            "학년:",
            grade_options[school_type],
            key="ai_grade"
        )
    
    with col2:
        topic_options = {
            "초등학교": ["일상생활", "가족", "학교생활", "취미", "음식", "동물", "계절/날씨"],
            "중학교": ["자기소개", "학교생활", "취미/여가활동", "음식/건강", "쇼핑/의류", "여행/교통", "환경/자연", "문화/전통"],
            "고등학교": ["자기계발", "학업/진로", "사회문제", "과학/기술", "환경/지속가능성", "문화/예술", "국제관계", "미디어/광고"]
        }
        
        topic = st.selectbox(
            "주제:",
            topic_options[school_type],
            key="ai_topic"
        )
        
        difficulty = st.selectbox(
            "난이도:",
            ["하", "중", "상"],
            key="ai_difficulty"
        )
    
    # 생성 버튼
    if st.button("문제 생성하기"):
        # API 키 확인
        if not st.session_state.openai_api_key and not st.session_state.gemini_api_key:
            st.error("문제 생성을 위해서는 OpenAI 또는 Google Gemini API 키가 필요합니다.")
            st.info("관리자에게 문의하거나, API 설정에서 키를 입력해주세요.")
            return
        
        # AI를 통한 문제 생성
        with st.spinner("AI가 영어 문제를 생성 중입니다... 잠시만 기다려주세요."):
            try:
                problems = None
                
                # OpenAI API 사용 시도
                if st.session_state.openai_api_key:
                    try:
                        client = openai.OpenAI(api_key=st.session_state.openai_api_key)
                        
                        # 프롬프트 작성
                        prompt = f"""
                        다음 조건에 맞는 영어 문제를 생성해주세요:
                        - 교육과정: {school_type} {grade}
                        - 주제: {topic}
                        - 난이도: {difficulty}
                        
                        문제 형식:
                        1. 객관식 문제 2개 (A, B, C, D 선택지)
                        2. 주관식 문제 1개 (짧은 답변)
                        3. 서술형 문제 1개 (긴 답변)
                        
                        각 문제에는 다음을 포함해 주세요:
                        - 문제 번호와 질문
                        - 상황 설명 (필요시)
                        - 객관식인 경우 선택지
                        - 정답
                        - 해설 (학습 포인트)
                        
                        문제 작성 시 참고사항:
                        - 학생들의 수준에 맞게 난이도 조절
                        - 문제마다 정답과 해설 필수
                        - 문화적 요소를 다양하게 포함
                        - 실생활에 활용 가능한 표현 위주
                        """
                        
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "system", "content": "You are an expert English teacher."},
                                     {"role": "user", "content": prompt}],
                            temperature=0.7
                        )
                        
                        problems = response.choices[0].message.content
                        
                    except Exception as e:
                        st.error(f"OpenAI API 오류: {str(e)}")
                        st.info("Google Gemini API로 시도합니다...")
                
                # Google Gemini API 사용 시도
                if not problems and st.session_state.gemini_api_key:
                    try:
                        genai.configure(api_key=st.session_state.gemini_api_key)
                        
                        # 사용 가능한 모델 목록 확인
                        available_models = []
                        try:
                            available_models = [m.name for m in genai.list_models()]
                        except Exception as e:
                            st.error(f"Gemini API 모델 목록 조회 오류: {str(e)}")
                            return
                        
                        gemini_models = [m for m in available_models if "gemini" in m.lower()]
                        
                        if not gemini_models:
                            st.error("사용 가능한 Gemini 모델이 없습니다. API 키를 확인하세요.")
                            return
                        
                        # 가장 적합한 모델 선택
                        model_name = "gemini-pro"
                        if model_name not in gemini_models:
                            model_name = gemini_models[0]
                            st.info(f"gemini-pro 모델을 사용할 수 없어 {model_name} 모델을 사용합니다.")
                        
                        try:
                            model = genai.GenerativeModel(model_name)
                            
                            # 프롬프트 작성
                            prompt = f"""
                            다음 조건에 맞는 영어 문제를 생성해주세요:
                            - 교육과정: {school_type} {grade}
                            - 주제: {topic}
                            - 난이도: {difficulty}
                            
                            문제 형식:
                            1. 객관식 문제 2개 (A, B, C, D 선택지)
                            2. 주관식 문제 1개 (짧은 답변)
                            3. 서술형 문제 1개 (긴 답변)
                            
                            각 문제에는 다음을 포함해 주세요:
                            - 문제 번호와 질문
                            - 상황 설명 (필요시)
                            - 객관식인 경우 선택지
                            - 정답
                            - 해설 (학습 포인트)
                            
                            문제 작성 시 참고사항:
                            - 학생들의 수준에 맞게 난이도 조절
                            - 문제마다 정답과 해설 필수
                            - 문화적 요소를 다양하게 포함
                            - 실생활에 활용 가능한 표현 위주
                            """
                            
                            response = model.generate_content(prompt)
                            
                            if response and hasattr(response, 'text'):
                                problems = response.text
                            else:
                                st.error("Gemini API가 유효한 응답을 반환하지 않았습니다.")
                                return
                        except Exception as e:
                            st.error(f"Gemini API 호출 중 오류 발생: {str(e)}")
                            st.info("API 키를 확인하고 다시 시도해보세요.")
                            return
                    
                    except Exception as e:
                        st.error(f"Gemini API 초기화 오류: {str(e)}")
                        return
                
                if problems and len(problems.strip()) > 0:
                    # 생성된 문제 표시
                    st.success("문제가 생성되었습니다. 검토 후 저장해주세요.")
                    
                    # 교사 검토를 위한 편집 가능한 텍스트 영역
                    edited_problems = st.text_area(
                        "생성된 문제 검토 및 수정",
                        value=problems,
                        height=400,
                        key="problem_edit_area"
                    )
                    
                    # 저장 버튼
                    if st.button("검토 완료 및 저장", key="save_problems"):
                        if not edited_problems.strip():
                            st.error("저장할 문제 내용이 없습니다.")
                            return
                        
                        success, message = save_generated_problems(
                            edited_problems,
                            school_type,
                            grade,
                            topic,
                            difficulty
                        )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.error("문제 생성에 실패했습니다. API 키를 확인하고 다시 시도해주세요.")
            
            except Exception as e:
                st.error(f"문제 생성 중 오류가 발생했습니다: {str(e)}")
                return

def teacher_problem_management():
    st.header("문제 관리")
    
    # 오른쪽 상단에 로그아웃 버튼 추가
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("로그아웃", key="problem_management_logout"):
            logout_user()
            st.rerun()
    
    tabs = st.tabs(["문제 목록", "직접 문제 제작", "CSV로 문제 업로드", "AI 문제 생성"])
    
    # 문제 목록 탭
    with tabs[0]:
        view_teacher_problems()
    
    # 직접 문제 제작 탭
    with tabs[1]:
        st.subheader("직접 문제 제작")
        
        # 여기에 문제 제작 폼 추가
        st.info("이 페이지에서 직접 영어 문제를 생성할 수 있습니다.")
        
        # 학교급 선택
        school_type = st.selectbox(
            "학교급:", 
            ["중학교", "고등학교"],
            help="학교 급별을 선택하세요.",
            key="manual_school_type"
        )
        
        # 학년 선택
        grade = st.selectbox(
            "학년:", 
            ["1학년", "2학년", "3학년"],
            help="학년을 선택하세요.",
            key="manual_grade"
        )
        
        # 주제 선택
        topic = st.selectbox(
            "주제:", 
            [
                "일상생활/자기소개",
                "학교생활/교육",
                "취미/여가활동",
                "환경/사회문제",
                "과학/기술",
                "문화/예술",
                "진로/직업"
            ],
            help="문제의 주제를 선택하세요.",
            key="manual_topic"
        )
        
        # 난이도 선택
        difficulty = st.selectbox(
            "난이도:", 
            ["하", "중", "상"],
            help="문제의 난이도를 선택하세요.",
            key="manual_difficulty"
        )
        
        # 문제 내용 입력
        problem_content = st.text_area(
            "문제 내용 (형식에 맞춰 입력해주세요):",
            height=400,
            help="""
            문제 형식 예시:
            
            [문제 1]
            유형: 객관식
            문제: What is the capital of the United Kingdom?
            맥락: Identifying capital cities of European countries.
            보기:
            A. Paris
            B. London
            C. Berlin
            D. Madrid
            정답: B
            해설: London is the capital city of the United Kingdom.
            
            [문제 2]
            ...
            """,
            key="manual_content"
        )
        
        if st.button("문제 저장", key="save_manual_problem"):
            if not problem_content.strip():
                st.error("문제 내용을 입력해주세요.")
            else:
                success, message = save_generated_problems(
                    problem_content,
                    school_type,
                    grade,
                    topic,
                    difficulty
                )
                
                if success:
                    st.success(message)
                    # 폼 초기화
                    st.session_state.manual_content = ""
                    st.rerun()
                else:
                    st.error(message)
    
    # CSV로 문제 업로드 탭
    with tabs[2]:
        st.subheader("CSV로 문제 업로드")
        st.info("CSV 파일로 문제를 일괄 업로드할 수 있습니다. 아래 양식에 맞춰 CSV 파일을 준비해주세요.")
        
        # CSV 템플릿 다운로드 링크
        st.markdown("""
        ### CSV 양식 안내
        아래 형식에 맞춰 CSV 파일을 준비해주세요:
        
        ```
        school_type,grade,topic,difficulty,question_type,question,context,options,answer,explanation
        중학교,1학년,일상생활/자기소개,하,객관식,"What is your name?","Basic personal introduction","A. My name is John. B. I am from Korea. C. I am 15 years old. D. I live in Seoul.",A,"This is how to introduce your name in English."
        ```
        
        - school_type: 학교급 (중학교, 고등학교)
        - grade: 학년 (1학년, 2학년, 3학년)
        - topic: 주제 (일상생활/자기소개, 학교생활/교육, 등)
        - difficulty: 난이도 (하, 중, 상)
        - question_type: 문제 유형 (객관식, 주관식, 서술형)
        - question: 문제 내용
        - context: 문제 상황 설명
        - options: 객관식 보기 (A. ... B. ... 형식)
        - answer: 정답
        - explanation: 해설
        """)
        