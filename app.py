import streamlit as st
import os
import openai
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import hashlib
import csv
import io
import datetime
import altair as alt
from dotenv import load_dotenv
from problems import SAMPLE_PROBLEMS
from prompts import get_correction_prompt

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="AI 영어 첨삭 앱",
    page_icon="✏️",
    layout="wide"
)

# 세션 상태 초기화 함수
def init_session_state():
    """모든 세션 상태 변수 초기화"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'current_problem' not in st.session_state:
        st.session_state.current_problem = None
    if 'user_answer' not in st.session_state:
        st.session_state.user_answer = ""
    if 'feedback' not in st.session_state:
        st.session_state.feedback = None
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = os.getenv('OPENAI_API_KEY', "")
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = os.getenv('GEMINI_API_KEY', "")
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
    if 'student_records' not in st.session_state:
        st.session_state.student_records = {}
    if 'teacher_problems' not in st.session_state:
        st.session_state.teacher_problems = {}
    if 'students' not in st.session_state:
        st.session_state.students = {}
    if 'teachers' not in st.session_state:
        st.session_state.teachers = {}
    if 'admins' not in st.session_state:
        st.session_state.admins = {'admin': hash_password('admin123')}  # 기본 관리자 계정

# 사용자 관리 함수
def hash_password(password):
    """비밀번호 해싱 함수"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """저장된 비밀번호와 입력된 비밀번호 확인"""
    return stored_password == hash_password(provided_password)

def load_users():
    """사용자 데이터 로드"""
    user_data = {
        'students': {},
        'teachers': {},
        'admins': {'admin': hash_password('admin123')}  # 기본 관리자 계정
    }
    
    # 파일이 존재하면 로드, 아니면 기본값 사용
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                user_data.update(loaded_data)
        except Exception as e:
            st.error(f"사용자 데이터 로드 중 오류 발생: {e}")
    
    return user_data

def save_users(user_data):
    """사용자 데이터 저장"""
    try:
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"사용자 데이터 저장 중 오류 발생: {e}")

def load_student_records():
    """학생 학습 기록 로드"""
    records = {}
    if os.path.exists('student_records.json'):
        try:
            with open('student_records.json', 'r', encoding='utf-8') as f:
                records = json.load(f)
        except Exception as e:
            st.error(f"학생 기록 로드 중 오류 발생: {e}")
    return records

def save_student_records(records):
    """학생 학습 기록 저장"""
    try:
        with open('student_records.json', 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"학생 기록 저장 중 오류 발생: {e}")

def load_teacher_problems():
    """교사가 출제한's 문제 로드"""
    problems = {}
    if os.path.exists('teacher_problems.json'):
        try:
            with open('teacher_problems.json', 'r', encoding='utf-8') as f:
                problems = json.load(f)
        except Exception as e:
            st.error(f"교사 문제 로드 중 오류 발생: {e}")
    return problems

def save_teacher_problems(problems):
    """교사가 출제한 문제 저장"""
    try:
        with open('teacher_problems.json', 'w', encoding='utf-8') as f:
            json.dump(problems, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"교사 문제 저장 중 오류 발생: {e}")

# 앱 초기화 및 데이터 로드
init_session_state()
users = load_users()
st.session_state.students = users['students']
st.session_state.teachers = users['teachers']
st.session_state.admins = users['admins']
st.session_state.student_records = load_student_records()
st.session_state.teacher_problems = load_teacher_problems()

# 로그인 페이지
def login_page():
    st.title("AI 영어 첨삭 앱")
    
    # 로그인 폼
    with st.form("login_form"):
        role = st.selectbox("사용자 유형", ["학생", "교사", "관리자"])
        username = st.text_input("사용자 이름")
        password = st.text_input("비밀번호", type="password")
        login_button = st.form_submit_button("로그인")
        
        if login_button:
            if role == "학생" and username in st.session_state.students:
                if verify_password(st.session_state.students[username], password):
                    st.session_state.logged_in = True
                    st.session_state.user_role = "student"
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
            elif role == "교사" and username in st.session_state.teachers:
                if verify_password(st.session_state.teachers[username], password):
                    st.session_state.logged_in = True
                    st.session_state.user_role = "teacher"
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
            elif role == "관리자" and username in st.session_state.admins:
                if verify_password(st.session_state.admins[username], password):
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
            else:
                st.error("사용자를 찾을 수 없습니다.")
    
    # 회원가입 섹션 (학생만 직접 가입 가능)
    st.subheader("회원가입 (학생)")
    with st.form("register_form"):
        new_username = st.text_input("새 사용자 이름")
        new_password = st.text_input("새 비밀번호", type="password")
        confirm_password = st.text_input("비밀번호 확인", type="password")
        register_button = st.form_submit_button("가입하기")
        
        if register_button:
            if new_username in st.session_state.students:
                st.error("이미 존재하는 사용자 이름입니다.")
            elif new_password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                st.session_state.students[new_username] = hash_password(new_password)
                users['students'] = st.session_state.students
                save_users(users)
                st.success("가입이 완료되었습니다. 이제 로그인할 수 있습니다.")

# 학생 대시보드
def student_dashboard():
    st.title(f"학생 대시보드 - {st.session_state.username}님 환영합니다!")
    
    # 사이드바 내비게이션
    st.sidebar.title("학생 메뉴")
    page = st.sidebar.radio("페이지 선택", ["문제 선택", "학습 기록", "프로필"])
    
    if page == "문제 선택":
        student_problem_page()
    elif page == "학습 기록":
        student_records_page()
    elif page == "프로필":
        student_profile_page()
    
    logout_button = st.sidebar.button("로그아웃")
    if logout_button:
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.rerun()

# 학생 문제 선택 페이지
def student_problem_page():
    st.header("연습 문제")
    
    # 문제 옵션
    problem_option = st.radio(
        "문제를 선택하세요:",
        ["예제 문제", "교사 출제 문제", "AI 생성 문제"],
        horizontal=True
    )
    
    # 문제가 변경되었을 때 첨삭 결과 초기화하는 함수
    def reset_feedback_if_problem_changed(new_problem_key):
        if st.session_state.last_problem_key != new_problem_key:
            st.session_state.user_answer = ""
            st.session_state.feedback = None
            st.session_state.last_problem_key = new_problem_key
            return True
        return False
    
    # 예제 문제 처리
    if problem_option == "예제 문제":
        # 카테고리별로 정렬
        categories = {}
        for key, problem in SAMPLE_PROBLEMS.items():
            category = problem.get("category", "기타")
            if category not in categories:
                categories[category] = []
            categories[category].append(key)
        
        # 카테고리 선택
        selected_category = st.selectbox(
            "카테고리를 선택하세요:",
            list(categories.keys())
        )
        
        # 선택된 카테고리의 문제 목록
        if selected_category:
            display_names = {}
            for key in categories[selected_category]:
                display_name = key.split('/')[-1] if '/' in key else key
                display_names[display_name] = key
                
            problem_display = st.selectbox(
                "문제를 선택하세요:",
                list(display_names.keys())
            )
            
            if problem_display:
                problem_key = display_names[problem_display]
                reset_feedback_if_problem_changed(problem_key)
                st.session_state.current_problem = SAMPLE_PROBLEMS[problem_key]
                display_problem_and_answer_form()
    
    # 교사 출제 문제 처리
    elif problem_option == "교사 출제 문제":
        # 교사별로 정렬
        teachers = {}
        for key, problem in st.session_state.teacher_problems.items():
            teacher = problem.get("teacher", "알 수 없음")
            if teacher not in teachers:
                teachers[teacher] = []
            teachers[teacher].append(key)
        
        if not teachers:
            st.info("현재 교사가 출제한 문제가 없습니다.")
        else:
            # 교사 선택
            selected_teacher = st.selectbox(
                "교사를 선택하세요:",
                list(teachers.keys())
            )
            
            # 선택된 교사의 문제 목록
            if selected_teacher:
                display_names = {}
                for key in teachers[selected_teacher]:
                    display_name = key.split('/')[-1] if '/' in key else key
                    display_names[display_name] = key
                    
                problem_display = st.selectbox(
                    "문제를 선택하세요:",
                    list(display_names.keys())
                )
                
                if problem_display:
                    problem_key = display_names[problem_display]
                    reset_feedback_if_problem_changed(problem_key)
                    st.session_state.current_problem = st.session_state.teacher_problems[problem_key]
                    display_problem_and_answer_form()
    
    # AI 생성 문제 처리
    elif problem_option == "AI 생성 문제":
        if not st.session_state.openai_api_key and not st.session_state.gemini_api_key:
            st.error("AI 문제 생성을 위한 API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
        else:
            # 주제 선택
            ai_topic_options = [
                "개인/일상생활", "여행/문화", "교육/학업", "사회/이슈", 
                "엔터테인먼트", "비즈니스/업무", "음식/요리", "스포츠/취미"
            ]
            ai_topic = st.selectbox("AI가 문제를 생성할 주제를 선택하세요:", ai_topic_options)
            
            # 난이도 선택
            st.subheader("난이도 선택")
            level_groups = ["초급", "중급", "상급"]
            level_details = {
                "초급": ["초", "중", "상"],
                "중급": ["초", "중", "상"],
                "상급": ["초", "중", "상"]
            }
            
            # 세션 상태 초기화
            if 'selected_level_group' not in st.session_state:
                st.session_state.selected_level_group = "초급"
            if 'selected_level_detail' not in st.session_state:
                st.session_state.selected_level_detail = "중"
                
            # 등급 선택 (초급, 중급, 상급)
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_group = st.radio(
                    "등급 선택:",
                    level_groups,
                    horizontal=True,
                    key="level_group",
                    index=level_groups.index(st.session_state.selected_level_group)
                )
                st.session_state.selected_level_group = selected_group
            
            # 세부 난이도 선택 (초, 중, 상)
            with col2:
                selected_detail = st.radio(
                    "세부 난이도:",
                    level_details[st.session_state.selected_level_group],
                    horizontal=True,
                    key="level_detail",
                    index=level_details[st.session_state.selected_level_group].index(st.session_state.selected_level_detail) 
                    if st.session_state.selected_level_detail in level_details[st.session_state.selected_level_group] else 1
                )
                st.session_state.selected_level_detail = selected_detail
            
            # 최종 선택된 난이도
            final_level = f"{st.session_state.selected_level_group}({st.session_state.selected_level_detail})"
            st.info(f"현재 선택된 난이도: **{final_level}**")
            
            if st.button("AI 문제 생성하기"):
                with st.spinner("AI가 문제를 생성 중입니다..."):
                    try:
                        # 생성 API 선택 (OpenAI 또는 Gemini)
                        if st.session_state.openai_api_key:
                            client = openai.OpenAI(api_key=st.session_state.openai_api_key)
                            response = client.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "system", "content": "You are an expert English teacher creating practice problems for Korean students."},
                                    {"role": "user", "content": f"""
                                    Create an English writing practice problem on the topic of {ai_topic} at {final_level} level for Korean students.
                                    
                                    Return the problem in JSON format with the following fields:
                                    - question: The writing prompt or question
                                    - context: Brief context or background for the question
                                    - example: A sample answer showing what a good response might look like
                                    
                                    Make sure the difficulty is appropriate for a {final_level} level Korean student learning English.
                                    """}
                                ],
                                temperature=0.7,
                            )
                            
                            ai_problem_text = response.choices[0].message.content
                        elif st.session_state.gemini_api_key:
                            # 제미나이 API 구현 (나중에 추가)
                            ai_problem_text = "{}"  # 임시 플레이스홀더
                            st.warning("제미나이 API 연동이 아직 구현되지 않았습니다.")
                        
                        # JSON 추출
                        import json
                        import re
                        
                        json_match = re.search(r'```json\n(.*?)\n```', ai_problem_text, re.DOTALL)
                        if json_match:
                            ai_problem_json = json.loads(json_match.group(1))
                        else:
                            try:
                                ai_problem_json = json.loads(ai_problem_text)
                            except:
                                st.error("AI 응답을 JSON으로 파싱할 수 없습니다.")
                                return
                        
                        # 현재 문제로 설정
                        st.session_state.current_problem = {
                            "category": ai_topic,
                            "question": ai_problem_json.get("question", ""),
                            "context": ai_problem_json.get("context", ""),
                            "example": ai_problem_json.get("example", "")
                        }
                        
                        # 문제 표시
                        st.success("AI가 새로운 문제를 생성했습니다!")
                        reset_feedback_if_problem_changed("ai_generated")
                        display_problem_and_answer_form()
                    except Exception as e:
                        st.error(f"문제 생성 중 오류가 발생했습니다: {e}")

# 문제 표시 및 답변 입력 양식
def display_problem_and_answer_form():
    st.subheader("문제")
    st.write(st.session_state.current_problem["question"])
    
    st.subheader("맥락")
    st.write(st.session_state.current_problem["context"])
    
    if st.session_state.current_problem.get("example"):
        st.subheader("예시 답안")
        st.write(st.session_state.current_problem["example"])
    
    st.header("답변 작성")
    
    # 입력 방법 선택
    input_method = st.radio(
        "답변 입력 방법을 선택하세요:",
        ["직접 텍스트 입력", "파일 업로드"],
        horizontal=True
    )
    
    user_answer = ""
    
    if input_method == "직접 텍스트 입력":
        user_answer = st.text_area(
            "답변을 영어로 작성하세요:",
            value=st.session_state.user_answer,
            height=200
        )
    elif input_method == "파일 업로드":
        uploaded_file = st.file_uploader("답변이 담긴 파일을 업로드하세요 (TXT 파일)", 
                                        type=["txt"])
        if uploaded_file is not None:
            try:
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                user_answer = stringio.read()
                st.write("파일에서 읽은 내용:")
                st.write(user_answer)
            except Exception as e:
                st.error(f"파일 읽기 중 오류가 발생했습니다: {e}")
    
    # 제출 버튼
    submit = st.button("첨삭 요청하기")
    
    if submit and user_answer:
        if not st.session_state.openai_api_key and not st.session_state.gemini_api_key:
            st.error("첨삭을 위한 API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
        else:
            st.session_state.user_answer = user_answer
            
            with st.spinner("AI가 첨삭 중입니다..."):
                try:
                    # API 선택 (OpenAI 또는 Gemini)
                    if st.session_state.openai_api_key:
                        client = openai.OpenAI(api_key=st.session_state.openai_api_key)
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": get_correction_prompt(st.session_state.current_problem, user_answer)}
                            ],
                            temperature=0.7,
                        )
                        
                        st.session_state.feedback = response.choices[0].message.content
                    elif st.session_state.gemini_api_key:
                        # 제미나이 API 구현 (나중에 추가)
                        st.session_state.feedback = "제미나이 API 연동이 아직 구현되지 않았습니다."
                    
                    # 학생 기록 저장
                    if st.session_state.username not in st.session_state.student_records:
                        st.session_state.student_records[st.session_state.username] = []
                    
                    # 문제 정보 및 답변/첨삭 기록
                    record = {
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "problem": st.session_state.current_problem,
                        "answer": user_answer,
                        "feedback": st.session_state.feedback
                    }
                    
                    st.session_state.student_records[st.session_state.username].append(record)
                    save_student_records(st.session_state.student_records)
                    
                except Exception as e:
                    st.error(f"API 호출 중 오류가 발생했습니다: {e}")
    
    # 첨삭 결과 표시
    if st.session_state.feedback:
        st.header("AI 첨삭 결과")
        st.markdown(st.session_state.feedback)
        
        # 결과 저장 버튼
        if st.button("결과 저장하기"):
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"feedback_{timestamp}.txt"
                filepath = os.path.join(st.session_state.save_dir, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"문제: {st.session_state.current_problem['question']}\n\n")
                    f.write(f"맥락: {st.session_state.current_problem['context']}\n\n")
                    f.write(f"나의 답변: {st.session_state.user_answer}\n\n")
                    f.write(f"AI 첨삭:\n{st.session_state.feedback}")
                
                st.success(f"첨삭 결과가 다음 파일로 저장되었습니다: {filepath}")
            except Exception as e:
                st.error(f"파일 저장 중 오류가 발생했습니다: {e}")

# 학생 학습 기록 페이지
def student_records_page():
    st.header("학습 기록")
    
    if st.session_state.username not in st.session_state.student_records or not st.session_state.student_records[st.session_state.username]:
        st.info("아직 학습 기록이 없습니다.")
        return
    
    records = st.session_state.student_records[st.session_state.username]
    
    # 기록 요약 통계
    st.subheader("학습 통계")
    total_problems = len(records)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 학습 문제 수", total_problems)
    with col2:
        st.metric("이번 주 학습 수", sum(1 for r in records if (
            datetime.datetime.now() - datetime.datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
        ).days <= 7))
    with col3:
        st.metric("오늘 학습 수", sum(1 for r in records if (
            datetime.datetime.now().date() == datetime.datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S").date()
        )))
    
    # 학습 기록 그래프
    if total_problems > 0:
        st.subheader("학습 활동")
        
        # 날짜별 학습량 데이터 준비
        date_counts = {}
        for record in records:
            date = datetime.datetime.strptime(record["timestamp"], "%Y-%m-%d %H:%M:%S").date().strftime("%Y-%m-%d")
            if date in date_counts:
                date_counts[date] += 1
            else:
                date_counts[date] = 1
        
        # 최근 14일 데이터만 표시
        dates = sorted(date_counts.keys())[-14:]
        counts = [date_counts.get(date, 0) for date in dates]
        
        # 차트 데이터 생성
        chart_data = pd.DataFrame({
            '날짜': dates,
            '학습 수': counts
        })
        
        # 차트 표시
        st.bar_chart(chart_data.set_index('날짜'))
    
    # 상세 기록 조회
    st.subheader("상세 기록")
    
    # 최신 기록부터 표시
    for i, record in enumerate(reversed(records)):
        with st.expander(f"학습 #{total_problems-i}: {record['timestamp']} - {record['problem']['question'][:30]}..."):
            st.write("**문제:**", record['problem']['question'])
            st.write("**맥락:**", record['problem']['context'])
            st.write("**내 답변:**", record['answer'])
            st.write("**AI 첨삭:**")
            st.markdown(record['feedback'])

# 학생 프로필 페이지
def student_profile_page():
    st.header("프로필 설정")
    
    # 비밀번호 변경
    st.subheader("비밀번호 변경")
    with st.form("change_password_form"):
        current_password = st.text_input("현재 비밀번호", type="password")
        new_password = st.text_input("
