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
    """교사가 출제한 문제 로드"""
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
        st.rerun()run()

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
        else:
            st.info("학습 활동 기록이 없습니다.")
    else:
        st.info("학습 기록이 없습니다.")
    
    # 시스템 정보
    st.subheader("앱 정보")
    st.write("**앱 버전:** 2.0.0")
    st.write("**마지막 업데이트:** 2025년 3월 31일")
    st.write("**프레임워크:** Streamlit")
    st.write("**AI 엔진:** OpenAI API, Gemini API")
    
    # 사용자 및 데이터 관리 옵션
    st.subheader("데이터 관리")
    
    if st.button("모든 데이터 초기화", help="주의: 이 작업은 되돌릴 수 없습니다."):
        confirm = st.checkbox("정말로 모든 데이터를 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다.", key="confirm_reset")
        
        if confirm and st.button("데이터 초기화 확인"):
            # 데이터 백업 생성
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 사용자 백업
            users = {
                'students': st.session_state.students,
                'teachers': st.session_state.teachers,
                'admins': st.session_state.admins
            }
            with open(os.path.join(backup_dir, f"users_before_reset_{timestamp}.json"), 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=4)
            
            # 학생 기록 백업
            with open(os.path.join(backup_dir, f"student_records_before_reset_{timestamp}.json"), 'w', encoding='utf-8') as f:
                json.dump(st.session_state.student_records, f, ensure_ascii=False, indent=4)
            
            # 교사 문제 백업
            with open(os.path.join(backup_dir, f"teacher_problems_before_reset_{timestamp}.json"), 'w', encoding='utf-8') as f:
                json.dump(st.session_state.teacher_problems, f, ensure_ascii=False, indent=4)
            
            # 데이터 초기화
            st.session_state.students = {}
            st.session_state.teachers = {}
            st.session_state.admins = {'admin': hash_password('admin123')}  # 기본 관리자 계정 유지
            st.session_state.student_records = {}
            st.session_state.teacher_problems = {}
            
            # 파일에 저장
            save_users({
                'students': {},
                'teachers': {},
                'admins': {'admin': hash_password('admin123')}
            })
            save_student_records({})
            save_teacher_problems({})
            
            st.success("모든 데이터가 초기화되었습니다. 백업이 'backups' 폴더에 저장되었습니다.")

# 메인 애플리케이션 로직
def main():
    # 로그인 상태에 따라 적절한 페이지 표시
    if not st.session_state.logged_in:
        login_page()
    else:
        # 역할에 따라 적절한 대시보드 표시
        if st.session_state.user_role == "student":
            student_dashboard()
        elif st.session_state.user_role == "teacher":
            teacher_dashboard()
        elif st.session_state.user_role == "admin":
            admin_dashboard()
        else:
            st.error("알 수 없는 사용자 역할입니다.")
            st.session_state.logged_in = False
            st.rerun()

if __name__ == "__main__":
    main()
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
        new_password = st.text_input("새 비밀번호", type="password")
        confirm_password = st.text_input("새 비밀번호 확인", type="password")
        change_password_button = st.form_submit_button("비밀번호 변경")
        
        if change_password_button:
            if not verify_password(st.session_state.students[st.session_state.username], current_password):
                st.error("현재 비밀번호가 일치하지 않습니다.")
            elif new_password != confirm_password:
                st.error("새 비밀번호가 일치하지 않습니다.")
            else:
                st.session_state.students[st.session_state.username] = hash_password(new_password)
                users = load_users()
                users['students'] = st.session_state.students
                save_users(users)
                st.success("비밀번호가 성공적으로 변경되었습니다.")

# 교사 대시보드
def teacher_dashboard():
    st.title(f"교사 대시보드 - {st.session_state.username}님 환영합니다!")
    
    # 사이드바 내비게이션
    st.sidebar.title("교사 메뉴")
    page = st.sidebar.radio("페이지 선택", ["문제 출제", "학생 관리", "채점 및 첨삭", "프로필"])
    
    if page == "문제 출제":
        teacher_problem_page()
    elif page == "학생 관리":
        teacher_student_management()
    elif page == "채점 및 첨삭":
        teacher_grading_page()
    elif page == "프로필":
        teacher_profile_page()
    
    logout_button = st.sidebar.button("로그아웃")
    if logout_button:
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.rerun()

# 교사 문제 출제 페이지
def teacher_problem_page():
    st.header("문제 출제")
    
    # 문제 출제 방법 선택
    problem_creation_method = st.radio(
        "문제 출제 방법을 선택하세요:",
        ["직접 작성", "CSV 파일 업로드", "AI로 생성"],
        horizontal=True
    )
    
    if problem_creation_method == "직접 작성":
        with st.form("create_problem_form"):
            st.subheader("새 문제 작성")
            
            problem_name = st.text_input("문제 이름 (고유 식별자):")
            category = st.selectbox(
                "카테고리:", 
                ["개인/일상생활", "여행/문화", "교육/학업", "사회/이슈", "엔터테인먼트", "비즈니스/업무", "음식/요리", "스포츠/취미", "기타"]
            )
            
            question = st.text_area("문제:", height=100)
            context = st.text_area("맥락:", height=100)
            example = st.text_area("예시 답안:", height=150)
            
            create_button = st.form_submit_button("문제 저장")
            
            if create_button:
                if not problem_name or not question or not context:
                    st.error("문제 이름, 문제, 맥락은 필수 입력사항입니다.")
                else:
                    # 문제 키 생성
                    problem_key = f"{category}/{problem_name}"
                    
                    # 문제 저장
                    st.session_state.teacher_problems[problem_key] = {
                        "teacher": st.session_state.username,
                        "category": category,
                        "question": question,
                        "context": context,
                        "example": example,
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    save_teacher_problems(st.session_state.teacher_problems)
                    st.success(f"문제 '{problem_name}'이(가) 성공적으로 저장되었습니다.")
        
        # 현재 출제한 문제 목록
        st.subheader("내가 출제한 문제")
        
        # 교사가 출제한 문제 필터링
        teacher_problems = {k: v for k, v in st.session_state.teacher_problems.items() 
                           if v.get("teacher") == st.session_state.username}
        
        if not teacher_problems:
            st.info("아직 출제한 문제가 없습니다.")
        else:
            # 카테고리별로 정렬
            categories = {}
            for key, problem in teacher_problems.items():
                category = problem.get("category", "기타")
                if category not in categories:
                    categories[category] = []
                categories[category].append((key, problem))
            
            for category, problems in categories.items():
                st.write(f"**{category}**")
                for key, problem in problems:
                    with st.expander(f"{key.split('/')[-1]}: {problem['question'][:50]}..."):
                        st.write("**문제:**", problem["question"])
                        st.write("**맥락:**", problem["context"])
                        st.write("**예시 답안:**", problem["example"])
                        st.write("**생성일:**", problem["created_at"])
                        
                        # 삭제 버튼
                        if st.button(f"삭제", key=f"del_{key}"):
                            del st.session_state.teacher_problems[key]
                            save_teacher_problems(st.session_state.teacher_problems)
                            st.success("문제가 삭제되었습니다.")
                            st.rerun()
    
    elif problem_creation_method == "CSV 파일 업로드":
        st.subheader("CSV 파일로 문제 업로드")
        
        st.markdown("""
        CSV 파일 형식:
        - 첫 번째 열: 문제 이름 (고유 식별자)
        - 두 번째 열: 카테고리
        - 세 번째 열: 문제
        - 네 번째 열: 맥락
        - 다섯 번째 열: 예시 답안
        
        첫 행은 헤더로 간주됩니다.
        """)
        
        uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])
        
        if uploaded_file is not None:
            try:
                # CSV 파일 읽기
                df = pd.read_csv(uploaded_file, encoding='utf-8')
                
                # 데이터 확인
                if len(df.columns) < 5:
                    st.error("CSV 파일은 최소 5개의 열이 필요합니다: 문제 이름, 카테고리, 문제, 맥락, 예시 답안")
                else:
                    # 데이터 미리보기
                    st.subheader("데이터 미리보기")
                    st.dataframe(df.head())
                    
                    # 열 이름 매핑
                    with st.form("csv_column_mapping"):
                        st.write("CSV 파일의 열을 필드에 매핑하세요:")
                        
                        name_col = st.selectbox("문제 이름 열:", df.columns, index=0)
                        category_col = st.selectbox("카테고리 열:", df.columns, index=1 if len(df.columns) > 1 else 0)
                        question_col = st.selectbox("문제 열:", df.columns, index=2 if len(df.columns) > 2 else 0)
                        context_col = st.selectbox("맥락 열:", df.columns, index=3 if len(df.columns) > 3 else 0)
                        example_col = st.selectbox("예시 답안 열:", df.columns, index=4 if len(df.columns) > 4 else 0)
                        
                        import_button = st.form_submit_button("문제 가져오기")
                        
                        if import_button:
                            # 문제 가져오기
                            imported_count = 0
                            for _, row in df.iterrows():
                                try:
                                    problem_name = str(row[name_col])
                                    category = str(row[category_col])
                                    
                                    # 유효한 카테고리 목록
                                    valid_categories = ["개인/일상생활", "여행/문화", "교육/학업", "사회/이슈", 
                                                      "엔터테인먼트", "비즈니스/업무", "음식/요리", "스포츠/취미", "기타"]
                                    
                                    # 카테고리가 유효하지 않으면 '기타'로 설정
                                    if category not in valid_categories:
                                        category = "기타"
                                    
                                    problem_key = f"{category}/{problem_name}"
                                    
                                    # 문제 저장
                                    st.session_state.teacher_problems[problem_key] = {
                                        "teacher": st.session_state.username,
                                        "category": category,
                                        "question": str(row[question_col]),
                                        "context": str(row[context_col]),
                                        "example": str(row[example_col]),
                                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    
                                    imported_count += 1
                                except Exception as e:
                                    st.error(f"행 가져오기 오류: {e}")
                            
                            # 변경사항 저장
                            save_teacher_problems(st.session_state.teacher_problems)
                            st.success(f"{imported_count}개의 문제를 성공적으로 가져왔습니다.")
                            
            except Exception as e:
                st.error(f"CSV 파일 처리 중 오류가 발생했습니다: {e}")
                
    elif problem_creation_method == "AI로 생성":
        st.subheader("AI로 문제 생성")
        
        if not st.session_state.openai_api_key and not st.session_state.gemini_api_key:
            st.error("AI 문제 생성을 위한 API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
        else:
            with st.form("ai_problem_generation"):
                # 주제 및 난이도 선택
                ai_topic_options = [
                    "개인/일상생활", "여행/문화", "교육/학업", "사회/이슈", 
                    "엔터테인먼트", "비즈니스/업무", "음식/요리", "스포츠/취미"
                ]
                
                ai_topic = st.selectbox("문제 주제:", ai_topic_options)
                problem_count = st.slider("생성할 문제 수:", 1, 5, 1)
                
                # 난이도 선택
                level_groups = ["초급", "중급", "상급"]
                selected_group = st.radio("난이도:", level_groups, horizontal=True)
                
                # 추가 지시사항
                additional_instructions = st.text_area("추가 지시사항 (선택사항):", 
                                                    placeholder="특정 어휘, 문법, 또는 주제 관련 세부 사항을 입력하세요.")
                
                generate_button = st.form_submit_button("AI로 문제 생성")
                
                if generate_button:
                    with st.spinner(f"AI가 {problem_count}개의 문제를 생성 중입니다..."):
                        try:
                            # API 선택 (OpenAI 또는 Gemini)
                            generated_problems = []
                            
                            if st.session_state.openai_api_key:
                                client = openai.OpenAI(api_key=st.session_state.openai_api_key)
                                
                                # 여러 문제 생성 요청
                                response = client.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=[
                                        {"role": "system", "content": "You are an expert English teacher creating practice problems for Korean students."},
                                        {"role": "user", "content": f"""
                                        Create {problem_count} English writing practice problem(s) on the topic of {ai_topic} at {selected_group} level for Korean students.
                                        
                                        {additional_instructions if additional_instructions else ""}
                                        
                                        Return the problems in JSON format with an array of problems with the following fields:
                                        - name: A short unique name for the problem
                                        - question: The writing prompt or question
                                        - context: Brief context or background for the question
                                        - example: A sample answer showing what a good response might look like
                                        
                                        The output should be a valid JSON with an array of problems.
                                        """}
                                    ],
                                    temperature=0.7,
                                )
                                
                                ai_response_text = response.choices[0].message.content
                                
                                # JSON 추출
                                import json
                                import re
                                
                                json_match = re.search(r'```json\n(.*?)\n```', ai_response_text, re.DOTALL)
                                if json_match:
                                    problems_data = json.loads(json_match.group(1))
                                else:
                                    try:
                                        problems_data = json.loads(ai_response_text)
                                    except:
                                        st.error("AI 응답을 JSON으로 파싱할 수 없습니다.")
                                        problems_data = {"problems": []}
                                
                                # JSON 형식에 따라 문제 추출
                                if isinstance(problems_data, list):
                                    generated_problems = problems_data
                                elif "problems" in problems_data:
                                    generated_problems = problems_data["problems"]
                                else:
                                    # 단일 문제인 경우
                                    generated_problems = [problems_data]
                            
                            elif st.session_state.gemini_api_key:
                                # 제미나이 API 구현 (나중에 추가)
                                st.warning("제미나이 API 연동이 아직 구현되지 않았습니다.")
                            
                            # 생성된 문제 표시 및 저장
                            if generated_problems:
                                st.success(f"{len(generated_problems)}개의 문제가 생성되었습니다.")
                                
                                # 저장 여부 확인
                                save_problems = st.checkbox("생성된 문제를 저장하시겠습니까?", value=True)
                                
                                for i, problem in enumerate(generated_problems):
                                    with st.expander(f"문제 #{i+1}: {problem.get('name', '') or problem.get('question', '')[:30]}..."):
                                        st.write("**문제:**", problem.get("question", ""))
                                        st.write("**맥락:**", problem.get("context", ""))
                                        st.write("**예시 답안:**", problem.get("example", ""))
                                
                                if save_problems and st.button("문제 저장하기"):
                                    saved_count = 0
                                    for problem in generated_problems:
                                        try:
                                            problem_name = problem.get("name", f"AI_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{saved_count}")
                                            problem_key = f"{ai_topic}/{problem_name}"
                                            
                                            # 문제 저장
                                            st.session_state.teacher_problems[problem_key] = {
                                                "teacher": st.session_state.username,
                                                "category": ai_topic,
                                                "question": problem.get("question", ""),
                                                "context": problem.get("context", ""),
                                                "example": problem.get("example", ""),
                                                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            }
                                            
                                            saved_count += 1
                                        except Exception as e:
                                            st.error(f"문제 저장 중 오류가 발생했습니다: {e}")
                                    
                                    # 변경사항 저장
                                    save_teacher_problems(st.session_state.teacher_problems)
                                    st.success(f"{saved_count}개의 문제가 성공적으로 저장되었습니다.")
                        
                        except Exception as e:
                            st.error(f"AI 문제 생성 중 오류가 발생했습니다: {e}")

# 교사 학생 관리 페이지
def teacher_student_management():
    st.header("학생 관리")
    
    tab1, tab2 = st.tabs(["학생 목록", "새 학생 등록"])
    
    with tab1:
        st.subheader("등록된 학생 목록")
        
        # 모든 학생 표시
        if not st.session_state.students:
            st.info("등록된 학생이 없습니다.")
        else:
            students_data = []
            for username in st.session_state.students:
                # 학생의 첨삭 기록 수 계산
                record_count = len(st.session_state.student_records.get(username, []))
                last_activity = "활동 없음"
                
                if username in st.session_state.student_records and st.session_state.student_records[username]:
                    # 마지막 활동 시간
                    last_activity = st.session_state.student_records[username][-1]["timestamp"]
                
                students_data.append({
                    "사용자명": username,
                    "첨삭 기록 수": record_count,
                    "마지막 활동": last_activity
                })
            
            # 데이터프레임으로 변환하여 표시
            students_df = pd.DataFrame(students_data)
            st.dataframe(students_df)
            
            # 학생 선택 및 상세 정보 보기
            selected_student = st.selectbox("학생 선택:", ["선택하세요..."] + list(st.session_state.students.keys()))
            
            if selected_student != "선택하세요...":
                st.subheader(f"{selected_student} 상세 정보")
                
                # 학생의 학습 통계
                if selected_student in st.session_state.student_records and st.session_state.student_records[selected_student]:
                    records = st.session_state.student_records[selected_student]
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
                    
                    # 최근 활동 목록
                    st.subheader("최근 활동")
                    for i, record in enumerate(reversed(records[:5])):  # 최근 5개 활동
                        with st.expander(f"학습 #{total_problems-i}: {record['timestamp']} - {record['problem']['question'][:30]}..."):
                            st.write("**문제:**", record['problem']['question'])
                            st.write("**맥락:**", record['problem']['context'])
                            st.write("**학생 답변:**", record['answer'])
                            st.write("**AI 첨삭:**")
                            st.markdown(record['feedback'])
                else:
                    st.info("이 학생의 학습 기록이 없습니다.")
                
                # 학생 비밀번호 초기화
                if st.button("비밀번호 초기화", key=f"reset_pw_{selected_student}"):
                    new_password = "password123"  # 기본 초기화 비밀번호
                    st.session_state.students[selected_student] = hash_password(new_password)
                    users = load_users()
                    users['students'] = st.session_state.students
                    save_users(users)
                    st.success(f"{selected_student}의 비밀번호가 '{new_password}'로 초기화되었습니다.")
                
                # 학생 삭제
                if st.button("학생 삭제", key=f"del_{selected_student}"):
                    del st.session_state.students[selected_student]
                    users = load_users()
                    users['students'] = st.session_state.students
                    save_users(users)
                    
                    # 학생 기록도 함께 삭제
                    if selected_student in st.session_state.student_records:
                        del st.session_state.student_records[selected_student]
                        save_student_records(st.session_state.student_records)
                    
                    st.success(f"학생 {selected_student}이(가) 삭제되었습니다.")
                    st.rerun()
    
    with tab2:
        st.subheader("새 학생 등록")
        
        with st.form("register_student_form"):
            new_username = st.text_input("사용자 이름")
            new_password = st.text_input("비밀번호", type="password")
            confirm_password = st.text_input("비밀번호 확인", type="password")
            
            register_button = st.form_submit_button("학생 등록")
            
            if register_button:
                if new_username in st.session_state.students:
                    st.error("이미 존재하는 사용자 이름입니다.")
                elif not new_username or not new_password:
                    st.error("사용자 이름과 비밀번호를 모두 입력해주세요.")
                elif new_password != confirm_password:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    # 학생 등록
                    st.session_state.students[new_username] = hash_password(new_password)
                    users = load_users()
                    users['students'] = st.session_state.students
                    save_users(users)
                    st.success(f"학생 {new_username}이(가) 성공적으로 등록되었습니다.")

# 교사 채점 및 첨삭 페이지
def teacher_grading_page():
    st.header("채점 및 첨삭")
    
    # 학생 선택
    students_with_records = [username for username in st.session_state.students 
                            if username in st.session_state.student_records 
                            and st.session_state.student_records[username]]
    
    if not students_with_records:
        st.info("학습 기록이 있는 학생이 없습니다.")
        return
        
    selected_student = st.selectbox("학생 선택:", ["선택하세요..."] + students_with_records)
    
    if selected_student != "선택하세요...":
        # 학생의 학습 기록 표시
        records = st.session_state.student_records[selected_student]
        
        if not records:
            st.info(f"{selected_student}의 학습 기록이 없습니다.")
            return
        
        # 학습 기록 선택
        record_descriptions = [f"{i+1}. {r['timestamp']} - {r['problem']['question'][:30]}..." 
                              for i, r in enumerate(records)]
        
        selected_record_idx = st.selectbox("채점할 기록 선택:", 
                                         range(len(record_descriptions)), 
                                         format_func=lambda i: record_descriptions[i])
        
        selected_record = records[selected_record_idx]
        
        # 선택된 기록 표시
        st.subheader("문제 정보")
        st.write("**문제:**", selected_record['problem']['question'])
        st.write("**맥락:**", selected_record['problem']['context'])
        
        st.subheader("학생 답변")
        st.write(selected_record['answer'])
        
        st.subheader("AI 첨삭")
        st.markdown(selected_record['feedback'])
        
        # 교사 점수 및 코멘트 입력
        st.subheader("교사 채점")
        
        # 이미 채점이 되어 있는지 확인
        if "teacher_score" in selected_record and "teacher_comment" in selected_record:
            current_score = selected_record["teacher_score"]
            current_comment = selected_record["teacher_comment"]
        else:
            current_score = 0
            current_comment = ""
        
        with st.form("teacher_grading_form"):
            score = st.slider("점수 (0-100)", 0, 100, current_score)
            comment = st.text_area("코멘트", value=current_comment, height=150)
            
            submit_grade = st.form_submit_button("채점 제출")
            
            if submit_grade:
                # 기록에 교사 채점 정보 추가
                selected_record["teacher_score"] = score
                selected_record["teacher_comment"] = comment
                selected_record["graded_by"] = st.session_state.username
                selected_record["graded_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 기록 저장
                save_student_records(st.session_state.student_records)
                st.success("채점이 성공적으로 저장되었습니다.")
                st.rerun()

# 교사 프로필 페이지
def teacher_profile_page():
    st.header("프로필 설정")
    
    # 비밀번호 변경
    st.subheader("비밀번호 변경")
    with st.form("teacher_change_password_form"):
        current_password = st.text_input("현재 비밀번호", type="password")
        new_password = st.text_input("새 비밀번호", type="password")
        confirm_password = st.text_input("새 비밀번호 확인", type="password")
        change_password_button = st.form_submit_button("비밀번호 변경")
        
        if change_password_button:
            if not verify_password(st.session_state.teachers[st.session_state.username], current_password):
                st.error("현재 비밀번호가 일치하지 않습니다.")
            elif new_password != confirm_password:
                st.error("새 비밀번호가 일치하지 않습니다.")
            else:
                st.session_state.teachers[st.session_state.username] = hash_password(new_password)
                users = load_users()
                users['teachers'] = st.session_state.teachers
                save_users(users)
                st.success("비밀번호가 성공적으로 변경되었습니다.")

# 관리자 대시보드
def admin_dashboard():
    st.title(f"관리자 대시보드 - {st.session_state.username}님 환영합니다!")
    
    # 사이드바 내비게이션
    st.sidebar.title("관리자 메뉴")
    page = st.sidebar.radio("페이지 선택", ["API 키 설정", "사용자 관리", "데이터 백업/복원", "시스템 정보"])
    
    if page == "API 키 설정":
        admin_api_page()
    elif page == "사용자 관리":
        admin_user_management()
    elif page == "데이터 백업/복원":
        admin_backup_page()
    elif page == "시스템 정보":
        admin_system_info()
    
    logout_button = st.sidebar.button("로그아웃")
    if logout_button:
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.re
