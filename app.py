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
import requests

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
if 'perplexity_api_key' not in st.session_state:
    # Perplexity API 키 추가
    st.session_state.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY", "")

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
    if 'perplexity_api_key' not in st.session_state:
        # Perplexity API 키 추가
        st.session_state.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY", "")

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
                st.session_state.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY", "")
                
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
    st.session_state.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY", "")

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

def perplexity_chat_completion(prompt, model="llama-3-sonar-small-32k", temperature=0.7):
    """Perplexity API를 사용하여 응답을 생성하는 함수"""
    try:
        api_key = st.session_state.perplexity_api_key
        if not api_key:
            return None, "Perplexity API 키가 설정되지 않았습니다."
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert English teacher."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"], None
        else:
            return None, f"Perplexity API 오류: {response.status_code} - {response.text}"
    
    except Exception as e:
        return None, f"Perplexity API 호출 중 오류 발생: {str(e)}"

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
        
        # Perplexity API 사용 시도
        elif 'perplexity_api_key' in st.session_state and st.session_state.perplexity_api_key:
            try:
                prompt = f"""
                다음 문제에 대한 학생의 답변을 평가해주세요:
                
                문제: {question}
                정답: {correct_answer}
                학생 답변: {user_answer}
                
                다음 형식으로 답변해주세요:
                1. 정확도 평가: 학생의 답변이 얼마나 정확한지 백분율로 표시
                2. 강점: 학생 답변의 강점
                3. 개선점: 학생 답변에서 개선이 필요한 부분
                4. 조언: 더 나은 답변을 위한 조언
                """
                
                feedback_content, error = perplexity_chat_completion(prompt)
                if feedback_content:
                    return feedback_content
                elif error:
                    # 오류 발생 시 Gemini API로 시도
                    st.error(f"Perplexity API 오류: {error}")
                    st.info("Google Gemini API로 시도합니다...")
                
            except Exception as e:
                st.error(f"Perplexity API 오류: {str(e)}")
                st.info("Google Gemini API로 시도합니다...")
        
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
    """교사 대시보드 페이지"""
    st.title("교사 대시보드 - 민현님")
    
    # 사이드바 메뉴
    menu = st.sidebar.radio(
        "메뉴 선택:",
        ["문제 관리", "학생 관리", "채점", "프로필", "API 설정"]
    )
    
    # 선택한 메뉴에 따라 다른 기능 표시
    if menu == "문제 관리":
        teacher_problem_management()
    elif menu == "학생 관리":
        teacher_student_management()
    elif menu == "채점":
        teacher_grading()
    elif menu == "프로필":
        teacher_profile()
    elif menu == "API 설정":
        admin_api_settings()

    # API 키 경고
    if not (st.session_state.openai_api_key or st.session_state.gemini_api_key or st.session_state.perplexity_api_key):
        st.warning("AI 기능을 사용하려면 OpenAI API 키, Google Gemini API 키 또는 Perplexity API 키가 필요합니다. 'API 설정' 메뉴에서 설정해주세요.")
    
    # Google Gemini API 연결 오류 표시
    if st.session_state.gemini_api_key and "teacher_problem_management" in st.session_state and st.session_state.teacher_problem_management.get("gemini_error"):
        st.error(f"Google Gemini API 연결 오류: {st.session_state.teacher_problem_management.get('gemini_error')}")
        st.info("다른 AI 모델(OpenAI 또는 Perplexity)을 사용하거나, API 설정에서 키를 확인해주세요.")
    
    # Perplexity API 연결 오류 표시
    if st.session_state.perplexity_api_key and "teacher_problem_management" in st.session_state and st.session_state.teacher_problem_management.get("perplexity_error"):
        st.error(f"Perplexity API 연결 오류: {st.session_state.teacher_problem_management.get('perplexity_error')}")
        st.info("다른 AI 모델(OpenAI 또는 Google Gemini)을 사용하거나, API 설정에서 키를 확인해주세요.")

def check_api_key():
    """API 키가 설정되어 있는지 확인하는 함수"""
    # 사용자가 선택한 AI 모델에 따라 키 체크
    selected_model = st.session_state.get('selected_model', "OpenAI GPT")  # 기본값 OpenAI
    
    if selected_model == "OpenAI GPT":
        return bool(st.session_state.get('openai_api_key', '').strip())
    elif selected_model == "Google Gemini":
        return bool(st.session_state.get('gemini_api_key', '').strip())
    elif selected_model == "Perplexity AI":
        return bool(st.session_state.get('perplexity_api_key', '').strip())
    else:
        # 셋 중 하나라도 설정되어 있으면 True
        return bool(st.session_state.get('openai_api_key', '').strip() or 
                   st.session_state.get('gemini_api_key', '').strip() or
                   st.session_state.get('perplexity_api_key', '').strip())

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
        if not st.session_state.openai_api_key and not st.session_state.gemini_api_key and not st.session_state.perplexity_api_key:
            st.error("문제 생성을 위해서는 OpenAI, Google Gemini 또는 Perplexity API 키가 필요합니다.")
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
                
                # Perplexity API 사용 시도
                if not problems and st.session_state.perplexity_api_key:
                    try:
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
                        
                        problems_content, error = perplexity_chat_completion(prompt)
                        if problems_content:
                            problems = problems_content
                        elif error:
                            st.error(f"Perplexity API 오류: {error}")
                            st.info("Google Gemini API로 시도합니다...")
                        
                    except Exception as e:
                        st.error(f"Perplexity API 오류: {str(e)}")
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
        
def save_learning_record(problems, answers, elapsed_time):
    """학생의 학습 기록을 저장하는 함수"""
    try:
        # 현재 사용자 정보
        username = st.session_state.username
        
        # 사용자 기록이 없으면 초기화
        if username not in st.session_state.student_records:
            st.session_state.student_records[username] = {
                "solved_problems": [],
                "total_problems": 0,
                "feedback_history": []
            }
        
        # 학습 기록 추가
        for i, (problem_id, problem_data) in enumerate(problems):
            # 인덱스 범위 내에서만 처리
            if i < len(answers):
                # 학습 결과 저장
                feedback = ""
                try:
                    # 답변과 정답이 있는 경우에만 피드백 생성
                    if answers[i] and problem_data.get('answer', ''):
                        feedback = generate_feedback(problem_data, answers[i])
                except Exception as e:
                    feedback = f"피드백 생성 중 오류: {str(e)}"
                
                # 기록 추가
                problem_record = {
                    "problem_id": problem_id,
                    "problem": problem_data,
                    "answer": answers[i],
                    "feedback": feedback,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "elapsed_time": elapsed_time
                }
                
                st.session_state.student_records[username]["solved_problems"].append(problem_record)
        
        # 총 문제 수 업데이트
        st.session_state.student_records[username]["total_problems"] += len(problems)
        
        # 데이터 저장
        save_users_data()
        
        return True
    except Exception as e:
        st.error(f"학습 기록 저장 중 오류가 발생했습니다: {str(e)}")
        return False

def teacher_student_management():
    """교사가 학생을 관리하는 기능"""
    st.header("학생 관리")
    
    # 교사가 등록한 학생만 필터링
    teacher_username = st.session_state.username
    teacher_students = {k: v for k, v in st.session_state.users.items() 
                       if v.get("role") == "student" and v.get("created_by") == teacher_username}
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["학생 등록", "학생 목록", "학습 진도 관리"])
    
    # 학생 등록 탭
    with tab1:
        st.subheader("새 학생 등록")
        
        username = st.text_input("학생 아이디:", key="new_student_username")
        name = st.text_input("이름:", key="new_student_name")
        email = st.text_input("이메일 (선택):", key="new_student_email")
        password = st.text_input("초기 비밀번호:", type="password", key="new_student_password")
        confirm_password = st.text_input("비밀번호 확인:", type="password", key="new_student_confirm")
        
        if st.button("학생 등록", key="register_student"):
            if not username or not name or not password:
                st.error("아이디, 이름, 비밀번호는 필수 입력사항입니다.")
            elif password != confirm_password:
                st.error("비밀번호와 비밀번호 확인이 일치하지 않습니다.")
            elif username in st.session_state.users:
                st.error(f"이미 존재하는 아이디입니다: {username}")
            elif len(password) < 6:
                st.error("비밀번호는 최소 6자 이상이어야 합니다.")
            else:
                # 학생 등록
                success, message = register_user(
                    username, 
                    password, 
                    "student", 
                    name, 
                    email, 
                    created_by=teacher_username
                )
                
                if success:
                    st.success(f"학생 '{name}'이(가) 성공적으로 등록되었습니다.")
                    st.rerun()
                else:
                    st.error(message)
    
    # 학생 목록 탭
    with tab2:
        st.subheader("등록된 학생 목록")
        
        if not teacher_students:
            st.info("등록된 학생이 없습니다. '학생 등록' 탭에서 새 학생을 등록해주세요.")
        else:
            # 표로 보여주기
            student_data_list = []
            for username, user_data in teacher_students.items():
                try:
                    created_at = datetime.datetime.fromisoformat(user_data.get("created_at", "")).strftime("%Y-%m-%d")
                except:
                    created_at = user_data.get("created_at", "")
                
                # 학습 통계 계산
                total_problems = 0
                if username in st.session_state.student_records:
                    total_problems = st.session_state.student_records[username].get("total_problems", 0)
                
                student_data_list.append({
                    "아이디": username,
                    "이름": user_data.get("name", ""),
                    "이메일": user_data.get("email", ""),
                    "등록일": created_at,
                    "푼 문제 수": total_problems
                })
            
            df = pd.DataFrame(student_data_list)
            st.dataframe(df, use_container_width=True)
            
            # 학생 삭제
            st.subheader("학생 삭제")
            selected_student = st.selectbox(
                "삭제할 학생 선택:",
                list(teacher_students.keys()),
                format_func=lambda x: f"{x} ({teacher_students[x].get('name', '')})"
            )
            
            if selected_student:
                st.warning(f"주의: 학생 계정을 삭제하면 모든 학습 기록도 함께 삭제됩니다.")
                st.info(f"삭제할 학생: {selected_student} ({teacher_students[selected_student].get('name', '')})")
                
                confirm_delete = st.checkbox("삭제를 확인합니다")
                
                if st.button("선택한 학생 삭제") and confirm_delete:
                    # 학생 삭제
                    if selected_student in st.session_state.users:
                        del st.session_state.users[selected_student]
                        
                        # 학생 기록도 삭제
                        if selected_student in st.session_state.student_records:
                            del st.session_state.student_records[selected_student]
                        
                        save_users_data()
                        st.success(f"학생 '{selected_student}'이(가) 삭제되었습니다.")
                        st.rerun()
    
    # 학습 진도 관리 탭
    with tab3:
        st.subheader("학생 학습 진도 관리")
        
        if not teacher_students:
            st.info("등록된 학생이 없습니다.")
        else:
            selected_student = st.selectbox(
                "학생 선택:",
                list(teacher_students.keys()),
                format_func=lambda x: f"{x} ({teacher_students[x].get('name', '')})",
                key="progress_student"
            )
            
            if selected_student:
                student_name = teacher_students[selected_student].get("name", selected_student)
                st.write(f"**{student_name}** 학생의 학습 현황")
                
                # 학습 통계
                if selected_student in st.session_state.student_records:
                    student_data = st.session_state.student_records[selected_student]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("총 학습 문제 수", student_data.get("total_problems", 0))
                    
                    with col2:
                        # 이번 주에 푼 문제 수
                        week_problems = 0
                        today = datetime.datetime.now()
                        week_start = today - datetime.timedelta(days=today.weekday())
                        
                        for problem in student_data.get("solved_problems", []):
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
                        
                        for problem in student_data.get("solved_problems", []):
                            try:
                                problem_time = datetime.datetime.fromisoformat(problem["timestamp"])
                                if problem_time >= today_start:
                                    today_problems += 1
                            except:
                                pass
                        
                        st.metric("오늘 학습 수", today_problems)
                    
                    # 학습 기록 표시
                    if student_data.get("solved_problems"):
                        st.subheader("최근 학습 기록")
                        
                        recent_problems = sorted(
                            student_data["solved_problems"], 
                            key=lambda x: x["timestamp"] if "timestamp" in x else "", 
                            reverse=True
                        )
                        
                        for i, problem in enumerate(recent_problems[:5]):  # 최근 5개만 표시
                            try:
                                with st.expander(f"{i+1}. {problem['problem']['question'][:50]}... ({datetime.datetime.fromisoformat(problem['timestamp']).strftime('%Y-%m-%d %H:%M')})"):
                                    st.write("**문제:**", problem["problem"]["question"])
                                    st.write("**학생 답변:**", problem["answer"])
                                    st.markdown("**AI 첨삭:**")
                                    st.markdown(problem["feedback"])
                            except Exception as e:
                                st.error(f"기록 {i+1}을 표시하는 데 문제가 발생했습니다: {str(e)}")
                    else:
                        st.info("아직 학습 기록이 없습니다.")
                else:
                    st.info("이 학생은 아직 문제를 풀지 않았습니다.")
        
def teacher_grading():
    """교사 채점 및 첨삭 기능"""
    st.header("채점 및 첨삭")
    
    # 교사가 등록한 학생만 필터링
    teacher_username = st.session_state.username
    teacher_students = {k: v for k, v in st.session_state.users.items() 
                       if v.get("role") == "student" and v.get("created_by") == teacher_username}
    
    if not teacher_students:
        st.info("등록된 학생이 없습니다. '학생 관리' 메뉴에서 학생을 먼저 등록해주세요.")
        return
    
    # 학생 선택
    selected_student = st.selectbox(
        "학생 선택:",
        list(teacher_students.keys()),
        format_func=lambda x: f"{x} ({teacher_students[x].get('name', '')})"
    )
    
    if not selected_student:
        st.info("학생을 선택해주세요.")
        return
    
    # 선택한 학생의 데이터 확인
    if selected_student not in st.session_state.student_records:
        st.info(f"선택한 학생({teacher_students[selected_student].get('name', '')})의 학습 기록이 없습니다.")
        return
    
    student_data = st.session_state.student_records[selected_student]
    
    # 학생이 푼 문제 목록 표시
    st.subheader(f"{teacher_students[selected_student].get('name', '')}의 채점 대상 문제")
    
    if not student_data.get("solved_problems"):
        st.info("이 학생은 아직 문제를 풀지 않았습니다.")
        return
    
    # 문제 목록을 날짜별로 정렬
    solved_problems = sorted(
        student_data["solved_problems"], 
        key=lambda x: x["timestamp"] if "timestamp" in x else "", 
        reverse=True
    )
    
    # 채점할 문제 선택
    problem_options = [
        f"{i+1}. {problem['problem']['question'][:40]}... ({datetime.datetime.fromisoformat(problem['timestamp']).strftime('%Y-%m-%d %H:%M')})"
        for i, problem in enumerate(solved_problems)
        if "timestamp" in problem
    ]
    
    selected_problem_idx = st.selectbox(
        "채점할 문제 선택:",
        range(len(problem_options)),
        format_func=lambda i: problem_options[i] if i < len(problem_options) else ""
    )
    
    if selected_problem_idx is not None and selected_problem_idx < len(solved_problems):
        # 선택한 문제 정보
        problem = solved_problems[selected_problem_idx]
        
        # 문제 및 답변 정보 표시
        st.markdown("### 문제 정보")
        st.markdown(f"**문제:** {problem['problem']['question']}")
        
        if 'context' in problem['problem'] and problem['problem']['context']:
            st.markdown(f"**상황:** {problem['problem']['context']}")
        
        st.markdown(f"**정답:** {problem['problem'].get('answer', 'N/A')}")
        
        st.markdown("### 학생 답변")
        st.markdown(f"**제출 답변:** {problem['answer']}")
        
        # 기존 피드백 표시
        st.markdown("### 현재 AI 피드백")
        st.markdown(problem.get('feedback', '피드백이 없습니다.'))
        
        # 교사 피드백 입력
        st.markdown("### 교사 첨삭")
        teacher_feedback = st.text_area(
            "추가 피드백을 입력하세요:",
            height=150,
            key="teacher_feedback"
        )
        
        if st.button("피드백 저장"):
            # 기존 피드백에 교사 피드백 추가
            updated_feedback = problem.get('feedback', '') + "\n\n**교사 첨삭:**\n" + teacher_feedback
            
            # 피드백 업데이트
            solved_problems[selected_problem_idx]['feedback'] = updated_feedback
            solved_problems[selected_problem_idx]['teacher_feedback'] = teacher_feedback
            solved_problems[selected_problem_idx]['graded_by'] = teacher_username
            solved_problems[selected_problem_idx]['graded_at'] = datetime.datetime.now().isoformat()
            
            # 데이터 저장
            save_users_data()
            
            st.success("첨삭이 저장되었습니다.")
            st.rerun()

def teacher_profile():
    """교사 프로필 관리 기능"""
    st.header("내 프로필")
    
    username = st.session_state.username
    user_data = st.session_state.users[username]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("기본 정보")
        st.write(f"**이름:** {user_data['name']}")
        st.write(f"**이메일:** {user_data['email']}")
        st.write(f"**사용자 유형:** 교사")
        
        if "created_at" in user_data:
            try:
                created_at = datetime.datetime.fromisoformat(user_data["created_at"])
                st.write(f"**가입일:** {created_at.strftime('%Y-%m-%d')}")
            except:
                st.write(f"**가입일:** {user_data['created_at']}")
    
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
    
    # 교사 활동 통계
    st.subheader("활동 통계")
    
    # 등록한 문제 수
    teacher_problems = len([p for p in st.session_state.teacher_problems.values() 
                           if p.get("created_by") == username])
    
    # 등록한 학생 수
    teacher_students = len([u for u in st.session_state.users.values() 
                           if u.get("role") == "student" and u.get("created_by") == username])
    
    # 첨삭한 문제 수
    graded_problems = 0
    for student, data in st.session_state.student_records.items():
        for problem in data.get("solved_problems", []):
            if problem.get("graded_by") == username:
                graded_problems += 1
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("등록한 문제 수", teacher_problems)
    with col2:
        st.metric("등록한 학생 수", teacher_students)
    with col3:
        st.metric("첨삭한 답변 수", graded_problems)
    
    # 전달사항 등록 (관리자에게)
    st.subheader("관리자에게 전달사항")
    message = st.text_area("관리자에게 전달할 메시지를 입력하세요:", height=100)
    
    if st.button("전달사항 제출"):
        if not message.strip():
            st.error("전달할 메시지를 입력해주세요.")
        else:
            # 메시지 저장 (실제로는 관리자에게 알림 기능 구현 필요)
            if "teacher_messages" not in st.session_state:
                st.session_state.teacher_messages = []
            
            st.session_state.teacher_messages.append({
                "from": username,
                "name": user_data.get("name", ""),
                "message": message,
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False
            })
            
            save_users_data()
            st.success("메시지가 관리자에게 전달되었습니다.")
    
def view_teacher_problems():
    """교사가 등록한 문제 목록 조회 및 관리"""
    st.subheader("문제 목록")
    
    # 현재 로그인한 교사가 만든 문제 필터링
    teacher_username = st.session_state.username
    teacher_problems = {k: v for k, v in st.session_state.teacher_problems.items() 
                       if v.get("created_by") == teacher_username}
    
    if not teacher_problems:
        st.info("등록된 문제가 없습니다. '직접 문제 제작' 또는 'AI 문제 생성' 탭에서 문제를 만들어보세요.")
        return
    
    # 검색 및 필터링
    search_col, filter_col1, filter_col2 = st.columns([3, 1, 1])
    
    with search_col:
        search_term = st.text_input("문제 검색:", placeholder="검색어 입력...")
    
    with filter_col1:
        filter_type = st.selectbox(
            "학교급 필터:",
            ["전체"] + list(set(p.get("school_type", "") for p in teacher_problems.values())),
            key="filter_school_type"
        )
    
    with filter_col2:
        filter_difficulty = st.selectbox(
            "난이도 필터:",
            ["전체", "하", "중", "상"],
            key="filter_difficulty"
        )
    
    # 필터링된 문제 목록
    filtered_problems = teacher_problems.copy()
    
    # 검색어 필터링
    if search_term:
        filtered_problems = {k: v for k, v in filtered_problems.items() 
                            if search_term.lower() in v.get("question", "").lower()}
    
    # 학교급 필터링
    if filter_type != "전체":
        filtered_problems = {k: v for k, v in filtered_problems.items() 
                            if v.get("school_type") == filter_type}
    
    # 난이도 필터링
    if filter_difficulty != "전체":
        filtered_problems = {k: v for k, v in filtered_problems.items() 
                            if v.get("difficulty") == filter_difficulty}
    
    # 표시할 컬럼 선택
    show_columns = st.multiselect(
        "표시할 컬럼:",
        ["문제", "학교급", "학년", "주제", "난이도", "문제유형", "생성일"],
        default=["문제", "학교급", "학년", "주제", "난이도"],
        key="show_columns"
    )
    
    # 문제 목록 데이터프레임 생성
    if filtered_problems:
        problem_data = []
        for problem_id, problem in filtered_problems.items():
            row = {
                "ID": problem_id,
                "문제": problem.get("question", "")[:50] + "..." if len(problem.get("question", "")) > 50 else problem.get("question", ""),
                "학교급": problem.get("school_type", ""),
                "학년": problem.get("grade", ""),
                "주제": problem.get("topic", ""),
                "난이도": problem.get("difficulty", ""),
                "문제유형": problem.get("question_type", "객관식"),
                "생성일": datetime.datetime.fromisoformat(problem.get("created_at", datetime.datetime.now().isoformat())).strftime("%Y-%m-%d") if "created_at" in problem else ""
            }
            problem_data.append(row)
        
        # 표시할 컬럼 필터링
        columns_to_show = ["ID"] + show_columns
        df = pd.DataFrame(problem_data)
        
        # 선택한 컬럼만 표시
        if set(columns_to_show).issubset(df.columns):
            df_display = df[columns_to_show]
            st.dataframe(df_display, use_container_width=True)
            
            # 문제 상세 보기
            selected_problem_id = st.selectbox(
                "문제 상세 보기:",
                options=list(filtered_problems.keys()),
                format_func=lambda x: filtered_problems[x].get("question", "")[:50] + "..." if len(filtered_problems[x].get("question", "")) > 50 else filtered_problems[x].get("question", "")
            )
            
            if selected_problem_id:
                problem = filtered_problems[selected_problem_id]
                
                with st.expander("문제 상세 정보", expanded=True):
                    # 문제 정보 표시
                    st.markdown(f"### {problem.get('question', '문제 내용 없음')}")
                    
                    if 'context' in problem and problem['context']:
                        st.markdown(f"**상황:** {problem['context']}")
                    
                    if 'options' in problem and problem['options']:
                        st.markdown("**선택지:**")
                        st.markdown(problem['options'])
                    
                    st.markdown(f"**정답:** {problem.get('answer', 'N/A')}")
                    
                    if 'explanation' in problem and problem['explanation']:
                        st.markdown(f"**해설:** {problem['explanation']}")
                    
                    # 문제 메타데이터
                    st.markdown("#### 문제 정보")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**학교급:** {problem.get('school_type', '')}")
                        st.write(f"**학년:** {problem.get('grade', '')}")
                    with col2:
                        st.write(f"**주제:** {problem.get('topic', '')}")
                        st.write(f"**난이도:** {problem.get('difficulty', '')}")
                    with col3:
                        st.write(f"**문제유형:** {problem.get('question_type', '객관식')}")
                        if 'created_at' in problem:
                            try:
                                created_at = datetime.datetime.fromisoformat(problem['created_at'])
                                st.write(f"**생성일:** {created_at.strftime('%Y-%m-%d')}")
                            except:
                                st.write(f"**생성일:** {problem['created_at']}")
                
                # 문제 편집/삭제 버튼
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("문제 편집", key=f"edit_{selected_problem_id}"):
                        st.session_state.editing_problem = selected_problem_id
                        st.session_state.editing_problem_data = problem.copy()
                
                with col2:
                    if st.button("문제 삭제", key=f"delete_{selected_problem_id}"):
                        # 삭제 확인
                        st.warning("이 문제를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
                        if st.button("삭제 확인", key=f"confirm_delete_{selected_problem_id}"):
                            # 문제 삭제
                            if selected_problem_id in st.session_state.teacher_problems:
                                del st.session_state.teacher_problems[selected_problem_id]
                                save_users_data()
                                st.success("문제가 삭제되었습니다.")
                                st.rerun()
            
            # 문제 편집 기능
            if 'editing_problem' in st.session_state and 'editing_problem_data' in st.session_state:
                with st.expander("문제 편집", expanded=True):
                    # 문제 데이터
                    problem_data = st.session_state.editing_problem_data
                    
                    # 문제 편집 폼
                    st.subheader("문제 편집")
                    
                    # 기본 정보
                    col1, col2 = st.columns(2)
                    with col1:
                        school_type = st.selectbox(
                            "학교급:",
                            ["초등학교", "중학교", "고등학교"],
                            index=["초등학교", "중학교", "고등학교"].index(problem_data.get("school_type", "중학교")) if problem_data.get("school_type") in ["초등학교", "중학교", "고등학교"] else 0
                        )
                        
                        grade_options = {
                            "초등학교": ["3학년", "4학년", "5학년", "6학년"],
                            "중학교": ["1학년", "2학년", "3학년"],
                            "고등학교": ["1학년", "2학년", "3학년"]
                        }
                        
                        grade = st.selectbox(
                            "학년:",
                            grade_options[school_type],
                            index=grade_options[school_type].index(problem_data.get("grade", grade_options[school_type][0])) if problem_data.get("grade") in grade_options[school_type] else 0
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
                            index=topic_options[school_type].index(problem_data.get("topic", topic_options[school_type][0])) if problem_data.get("topic") in topic_options[school_type] else 0
                        )
                        
                        difficulty = st.selectbox(
                            "난이도:",
                            ["하", "중", "상"],
                            index=["하", "중", "상"].index(problem_data.get("difficulty", "중")) if problem_data.get("difficulty") in ["하", "중", "상"] else 1
                        )
                    
                    # 문제 내용
                    question_type = st.selectbox(
                        "문제 유형:",
                        ["객관식", "주관식", "서술형"],
                        index=["객관식", "주관식", "서술형"].index(problem_data.get("question_type", "객관식")) if problem_data.get("question_type") in ["객관식", "주관식", "서술형"] else 0
                    )
                    
                    question = st.text_area("문제:", value=problem_data.get("question", ""), height=100)
                    context = st.text_area("상황 설명:", value=problem_data.get("context", ""), height=50)
                    
                    if question_type == "객관식":
                        options = st.text_area(
                            "선택지 (각 선택지는 A. B. 형식으로 시작):",
                            value=problem_data.get("options", ""),
                            height=150
                        )
                    else:
                        options = ""
                    
                    answer = st.text_area("정답:", value=problem_data.get("answer", ""), height=50)
                    explanation = st.text_area("해설:", value=problem_data.get("explanation", ""), height=100)
                    
                    if st.button("변경사항 저장"):
                        # 업데이트된 문제 데이터
                        updated_problem = {
                            "school_type": school_type,
                            "grade": grade,
                            "topic": topic,
                            "difficulty": difficulty,
                            "question_type": question_type,
                            "question": question,
                            "context": context,
                            "options": options,
                            "answer": answer,
                            "explanation": explanation,
                            "created_by": problem_data.get("created_by", teacher_username),
                            "created_at": problem_data.get("created_at", datetime.datetime.now().isoformat()),
                            "updated_at": datetime.datetime.now().isoformat()
                        }
                        
                        # 문제 업데이트
                        st.session_state.teacher_problems[st.session_state.editing_problem] = updated_problem
                        save_users_data()
                        
                        # 편집 상태 초기화
                        del st.session_state.editing_problem
                        del st.session_state.editing_problem_data
                        
                        st.success("문제가 업데이트되었습니다.")
                        st.rerun()
                    
                    if st.button("취소"):
                        # 편집 상태 초기화
                        del st.session_state.editing_problem
                        del st.session_state.editing_problem_data
                        st.rerun()
    else:
        st.info("검색 조건에 맞는 문제가 없습니다.")
    
def parse_problems(text):
    """AI가 생성한 문제 텍스트를 파싱하여 구조화된 문제 목록으로 변환합니다."""
    try:
        # 결과를 저장할 리스트
        problems = []
        
        # 문제 분리 패턴 (숫자로 시작하거나 '문제 1' 형태로 시작하는 줄)
        problem_pattern = r'(?:^|\n)(?:\d+[\.\):]|문제\s*\d+[\.\):])'
        
        # 문제 텍스트 분리
        problem_texts = re.split(problem_pattern, text)
        
        # 첫 번째 항목이 빈 문자열이거나 의미 없는 경우 제거
        if problem_texts and (not problem_texts[0].strip() or len(problem_texts[0]) < 10):
            problem_texts = problem_texts[1:]
        
        # 문제 번호 추출 (몇 번 문제인지 확인용)
        problem_numbers = re.findall(problem_pattern, text)
        
        # 매칭된 문제 번호가 없으면 단일 문제로 처리
        if not problem_numbers and text.strip():
            problem_texts = [text]
        
        # 각 문제 텍스트 파싱
        for i, problem_text in enumerate(problem_texts):
            if not problem_text.strip():
                continue
            
            problem = {}
            
            # 문제 본문 추출
            lines = problem_text.strip().split('\n')
            
            # 질문과 내용 분리
            question_text = lines[0].strip() if lines else ""
            
            # 질문이 너무 짧으면 여러 줄 합치기
            if len(question_text) < 10 and len(lines) > 1:
                question_text = " ".join([line.strip() for line in lines[:2]])
            
            problem["question"] = question_text
            
            # 문제 내용 전체
            problem["content"] = problem_text
            
            # 선택지 추출 (객관식 문제인 경우)
            options_pattern = r'(?:^|\n)(?:[A-D][\.\)])'
            if re.search(options_pattern, problem_text):
                problem["question_type"] = "객관식"
                
                # 선택지 텍스트 추출
                options_text = re.findall(r'(?:[A-D][\.\)].*(?:\n|$))+', problem_text)
                if options_text:
                    problem["options"] = "\n".join(options_text)
            else:
                # 선택지가 없으면 주관식 또는 서술형으로 판단
                # 일단 주관식으로 기본 설정하고, 나중에 문제 내용에 따라 서술형으로 변경 가능
                problem["question_type"] = "주관식"
                problem["options"] = ""
            
            # 정답 추출 (Answer, 정답, 답 등으로 시작하는 줄)
            answer_pattern = r'(?:^|\n)(?:Answer|정답|답)[\s\:]+(.+?)(?:\n|$)'
            answer_match = re.search(answer_pattern, problem_text, re.IGNORECASE)
            
            if answer_match:
                problem["answer"] = answer_match.group(1).strip()
            else:
                # 정답 패턴이 없으면 텍스트에서 가능한 정답 추출 시도
                for line in lines:
                    if '정답' in line or 'answer' in line.lower() or '답:' in line or '답은' in line:
                        # 콜론이나 '은/는' 이후의 텍스트를 정답으로 추출
                        if ':' in line:
                            problem["answer"] = line.split(':', 1)[1].strip()
                        elif '는' in line:
                            problem["answer"] = line.split('는', 1)[1].strip()
                        elif '은' in line:
                            problem["answer"] = line.split('은', 1)[1].strip()
                        else:
                            problem["answer"] = line.replace('정답', '').replace('Answer', '').replace('답', '').strip()
                        break
                
                # 여전히 정답이 없으면 빈 문자열 설정
                if "answer" not in problem:
                    problem["answer"] = ""
            
            # 해설 추출 (Explanation, 해설 등으로 시작하는 줄)
            explanation_pattern = r'(?:^|\n)(?:Explanation|해설|설명)[\s\:]+(.+(?:\n.+)*)'
            explanation_match = re.search(explanation_pattern, problem_text, re.IGNORECASE)
            
            if explanation_match:
                problem["explanation"] = explanation_match.group(1).strip()
            else:
                # 다른 패턴 시도
                for line_idx, line in enumerate(lines):
                    if '해설' in line or 'explanation' in line.lower() or '설명' in line:
                        if line_idx < len(lines) - 1:
                            problem["explanation"] = "\n".join(lines[line_idx+1:])
                            break
                
                # 해설이 없으면 빈 문자열 설정
                if "explanation" not in problem:
                    problem["explanation"] = ""
            
            # 서술형 판단 (주관식이면서 정답이 긴 경우)
            if problem["question_type"] == "주관식" and len(problem.get("answer", "")) > 30:
                problem["question_type"] = "서술형"
            
            problems.append(problem)
        
        return problems
    
    except Exception as e:
        st.error(f"문제 파싱 중 오류가 발생했습니다: {str(e)}")
        return []
    
def admin_api_settings():
    """API 키 설정"""
    st.header("API 설정")
    
    # 현재 API 키 상태
    openai_key_status = "설정됨 ✅" if st.session_state.openai_api_key else "설정되지 않음 ❌"
    gemini_key_status = "설정됨 ✅" if st.session_state.gemini_api_key else "설정되지 않음 ❌"
    perplexity_key_status = "설정됨 ✅" if st.session_state.perplexity_api_key else "설정되지 않음 ❌"
    
    st.info("API 키는 .env 파일에 저장되며, 애플리케이션 재시작 시 해당 파일에서 불러옵니다.")
    st.warning("주의: API 키는 암호화되지 않은 일반 텍스트로 저장됩니다.")
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["OpenAI API", "Google Gemini API", "Perplexity API"])
    
    with tab1:
        st.subheader(f"OpenAI API 키 ({openai_key_status})")
        openai_api_key = st.text_input(
            "OpenAI API 키 입력:",
            type="password",
            value=st.session_state.openai_api_key,
            help="https://platform.openai.com/account/api-keys에서 API 키를 발급받을 수 있습니다."
        )
        
        if st.button("OpenAI API 키 저장", key="save_openai"):
            if openai_api_key:
                # API 키 세션 상태 업데이트
                st.session_state.openai_api_key = openai_api_key.strip()
                
                # .env 파일에 API 키 저장
                try:
                    # 현재 .env 파일 내용 읽기
                    env_content = ""
                    if os.path.exists(".env"):
                        with open(".env", "r") as f:
                            env_content = f.read()
                    
                    # OPENAI_API_KEY가 이미 있는지 확인
                    if "OPENAI_API_KEY" in env_content:
                        # 기존 값 업데이트
                        import re
                        env_content = re.sub(
                            r'OPENAI_API_KEY=.*', 
                            f'OPENAI_API_KEY="{openai_api_key.strip()}"', 
                            env_content
                        )
                    else:
                        # 키 추가
                        env_content += f'\nOPENAI_API_KEY="{openai_api_key.strip()}"\n'
                    
                    # 변경된 내용 저장
                    with open(".env", "w") as f:
                        f.write(env_content)
                    
                    st.success("OpenAI API 키가 성공적으로 저장되었습니다!")
                except Exception as e:
                    st.error(f"API 키 저장 중 오류가 발생했습니다: {str(e)}")
            else:
                st.warning("API 키를 입력해주세요.")
        
        # API 키 테스트
        if st.button("OpenAI API 키 테스트", key="test_openai"):
            if not st.session_state.openai_api_key:
                st.warning("API 키가 설정되지 않았습니다.")
            else:
                with st.spinner("OpenAI API 키를 테스트 중입니다..."):
                    try:
                        client = openai.OpenAI(api_key=st.session_state.openai_api_key)
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": "Hello, are you working?"}],
                            max_tokens=10
                        )
                        st.success("OpenAI API 키가 정상적으로 작동합니다!")
                    except Exception as e:
                        st.error(f"OpenAI API 키 테스트 중 오류가 발생했습니다: {str(e)}")
    
    with tab2:
        st.subheader(f"Google Gemini API 키 ({gemini_key_status})")
        gemini_api_key = st.text_input(
            "Google Gemini API 키 입력:",
            type="password",
            value=st.session_state.gemini_api_key,
            help="https://makersuite.google.com/app/apikey에서 API 키를 발급받을 수 있습니다."
        )
        
        if st.button("Google Gemini API 키 저장", key="save_gemini"):
            if gemini_api_key:
                # API 키 세션 상태 업데이트
                st.session_state.gemini_api_key = gemini_api_key.strip()
                
                # .env 파일에 API 키 저장
                try:
                    # 현재 .env 파일 내용 읽기
                    env_content = ""
                    if os.path.exists(".env"):
                        with open(".env", "r") as f:
                            env_content = f.read()
                    
                    # GOOGLE_API_KEY가 이미 있는지 확인
                    if "GOOGLE_API_KEY" in env_content:
                        # 기존 값 업데이트
                        import re
                        env_content = re.sub(
                            r'GOOGLE_API_KEY=.*', 
                            f'GOOGLE_API_KEY="{gemini_api_key.strip()}"', 
                            env_content
                        )
                    else:
                        # 키 추가
                        env_content += f'\nGOOGLE_API_KEY="{gemini_api_key.strip()}"\n'
                    
                    # GEMINI_API_KEY 제거 (통합)
                    if "GEMINI_API_KEY" in env_content:
                        env_content = re.sub(r'GEMINI_API_KEY=.*\n', '', env_content)
                    
                    # 변경된 내용 저장
                    with open(".env", "w") as f:
                        f.write(env_content)
                    
                    st.success("Google Gemini API 키가 성공적으로 저장되었습니다!")
                except Exception as e:
                    st.error(f"API 키 저장 중 오류가 발생했습니다: {str(e)}")
            else:
                st.warning("API 키를 입력해주세요.")
        
        # API 키 테스트
        if st.button("Google Gemini API 키 테스트", key="test_gemini"):
            if not st.session_state.gemini_api_key:
                st.warning("API 키가 설정되지 않았습니다.")
            else:
                with st.spinner("Google Gemini API 키를 테스트 중입니다..."):
                    try:
                        genai.configure(api_key=st.session_state.gemini_api_key)
                        
                        # 사용 가능한 모델 목록 확인
                        available_models = [m.name for m in genai.list_models()]
                        gemini_models = [m for m in available_models if "gemini" in m.lower()]
                        
                        if gemini_models:
                            st.success(f"Google Gemini API 키가 정상적으로 작동합니다! 사용 가능한 모델: {', '.join(gemini_models[:3])}...")
                        else:
                            st.warning("API 키는 유효하지만 Gemini 모델을 사용할 수 없습니다. 계정 권한을 확인하세요.")
                    except Exception as e:
                        st.error(f"Google Gemini API 키 테스트 중 오류가 발생했습니다: {str(e)}")
    
    with tab3:
        st.subheader(f"Perplexity API 키 ({perplexity_key_status})")
        perplexity_api_key = st.text_input(
            "Perplexity API 키 입력:",
            type="password",
            value=st.session_state.perplexity_api_key,
            help="https://www.perplexity.ai/settings/api에서 API 키를 발급받을 수 있습니다."
        )
        
        if st.button("Perplexity API 키 저장", key="save_perplexity"):
            if perplexity_api_key:
                # API 키 세션 상태 업데이트
                st.session_state.perplexity_api_key = perplexity_api_key.strip()
                
                # .env 파일에 API 키 저장
                try:
                    # 현재 .env 파일 내용 읽기
                    env_content = ""
                    if os.path.exists(".env"):
                        with open(".env", "r") as f:
                            env_content = f.read()
                    
                    # PERPLEXITY_API_KEY가 이미 있는지 확인
                    if "PERPLEXITY_API_KEY" in env_content:
                        # 기존 값 업데이트
                        import re
                        env_content = re.sub(
                            r'PERPLEXITY_API_KEY=.*', 
                            f'PERPLEXITY_API_KEY="{perplexity_api_key.strip()}"', 
                            env_content
                        )
                    else:
                        # 키 추가
                        env_content += f'\nPERPLEXITY_API_KEY="{perplexity_api_key.strip()}"\n'
                    
                    # 변경된 내용 저장
                    with open(".env", "w") as f:
                        f.write(env_content)
                    
                    st.success("Perplexity API 키가 성공적으로 저장되었습니다!")
                except Exception as e:
                    st.error(f"API 키 저장 중 오류가 발생했습니다: {str(e)}")
            else:
                st.warning("API 키를 입력해주세요.")
        
        # API 키 테스트
        if st.button("Perplexity API 키 테스트", key="test_perplexity"):
            if not st.session_state.perplexity_api_key:
                st.warning("API 키가 설정되지 않았습니다.")
            else:
                with st.spinner("Perplexity API 키를 테스트 중입니다..."):
                    try:
                        # 간단한 API 호출
                        content, error = perplexity_chat_completion("Hello, are you working?")
                        
                        if content and not error:
                            st.success("Perplexity API 키가 정상적으로 작동합니다!")
                        else:
                            st.error(f"Perplexity API 키 테스트 중 오류가 발생했습니다: {error}")
                    except Exception as e:
                        st.error(f"Perplexity API 키 테스트 중 오류가 발생했습니다: {str(e)}")
    
    st.divider()
    
    # AI 모델 선택
    st.subheader("기본 AI 모델 설정")
    
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "OpenAI GPT"
    
    model_options = ["OpenAI GPT", "Google Gemini", "Perplexity AI"]
    
    selected_model = st.radio(
        "기본 AI 모델:",
        model_options,
        index=model_options.index(st.session_state.selected_model)
    )
    
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model
        st.success(f"기본 AI 모델이 {selected_model}로 설정되었습니다.")
        
        # 선택한 모델에 API 키가 설정되어 있는지 확인
        if selected_model == "OpenAI GPT" and not st.session_state.openai_api_key:
            st.warning("OpenAI API 키가 설정되어 있지 않습니다.")
        elif selected_model == "Google Gemini" and not st.session_state.gemini_api_key:
            st.warning("Google Gemini API 키가 설정되어 있지 않습니다.")
        elif selected_model == "Perplexity AI" and not st.session_state.perplexity_api_key:
            st.warning("Perplexity API 키가 설정되어 있지 않습니다.")
    