import streamlit as st
import os
import openai
import pandas as pd
from dotenv import load_dotenv
from problems import SAMPLE_PROBLEMS
from prompts import get_correction_prompt
import io
import datetime
import altair as alt

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI 영어 첨삭 앱",
    page_icon="✏️",
    layout="wide"
)

# App title and description
st.title("AI 영어 첨삭 앱")
st.markdown("""
이 앱은 당신의 영어 문장을 AI가 첨삭해주는 서비스입니다.
문제를 선택하거나 직접 입력한 후, 당신의 답변을 작성하면 AI가 피드백을 제공합니다.
""")

# Initialize session state for storing user inputs and responses
if 'current_problem' not in st.session_state:
    st.session_state.current_problem = None
if 'user_answer' not in st.session_state:
    st.session_state.user_answer = ""
if 'feedback' not in st.session_state:
    st.session_state.feedback = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
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

# Sidebar for app navigation and API key input
st.sidebar.title("메뉴")

# API Key input in sidebar
api_key = st.sidebar.text_input("OpenAI API 키를 입력하세요:", 
                               value=st.session_state.api_key, 
                               type="password",
                               help="API 키는 안전하게 저장되며 이 세션에서만 사용됩니다.")
if api_key:
    st.session_state.api_key = api_key

# 저장 경로 설정
save_dir = st.sidebar.text_input("결과 저장 경로 (비워두면 현재 폴더):", 
                              value=st.session_state.save_dir)
if save_dir and os.path.isdir(save_dir):
    st.session_state.save_dir = save_dir
elif save_dir:
    st.sidebar.warning(f"경로 '{save_dir}'가 존재하지 않습니다. 현재 폴더를 사용합니다.")
    st.session_state.save_dir = os.getcwd()

reset_button = st.sidebar.button("새로운 문제로 시작하기")
if reset_button:
    st.session_state.current_problem = None
    st.session_state.user_answer = ""
    st.session_state.feedback = None
    st.session_state.last_problem_key = None
    st.rerun()

# Main app layout
st.header("연습 문제")

# Problem selection
problem_option = st.radio(
    "문제를 선택하거나 직접 입력하세요:",
    ["예제 문제 선택", "직접 문제 입력", "AI가 생성한 문제"],
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

# Handle problem selection
if problem_option == "예제 문제 선택":
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
        # 문제 이름만 보여주기 위해 키에서 카테고리 부분 제거
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
            
            # 문제가 변경되었는지 확인하고 필요시 초기화
            problem_changed = reset_feedback_if_problem_changed(problem_key)
            
            st.session_state.current_problem = SAMPLE_PROBLEMS[problem_key]
            
            # Display the selected problem
            st.subheader("문제")
            st.write(st.session_state.current_problem["question"])
            
            st.subheader("맥락")
            st.write(st.session_state.current_problem["context"])
            
            st.subheader("예시 답안")
            st.write(st.session_state.current_problem["example"])
            
elif problem_option == "직접 문제 입력":
    # 직접 입력할 때도 이전 문제와 다른 것으로 간주
    reset_feedback_if_problem_changed("custom_input")
    
    # Custom problem input
    custom_question = st.text_area("문제를 입력하세요:", height=100)
    custom_context = st.text_area("문제의 맥락을 입력하세요:", height=100)
    custom_example = st.text_area("예시 답안을 입력하세요 (선택사항):", height=100)
    
    save_custom = st.checkbox("이 문제를 저장하여 나중에 다시 사용하기")
    custom_name = ""
    custom_category = ""
    
    if save_custom:
        custom_category = st.selectbox(
            "문제 카테고리:", 
            ["개인/일상생활", "여행/문화", "교육/학업", "사회/이슈", "엔터테인먼트", "비즈니스/업무", "음식/요리", "기타"]
        )
        custom_name = st.text_input("이 문제의 이름을 입력하세요:")
    
    if custom_question and custom_context:
        if st.button("문제 설정하기"):
            st.session_state.current_problem = {
                "category": custom_category if custom_category else "기타",
                "question": custom_question,
                "context": custom_context,
                "example": custom_example  # 빈 문자열일 수 있음
            }
            
            # 문제 저장
            if save_custom and custom_name:
                problem_key = f"{custom_category}/{custom_name}" if custom_category else custom_name
                st.session_state.custom_problems[problem_key] = st.session_state.current_problem
                st.success(f"문제 '{custom_name}'이(가) 저장되었습니다.")
                
else:  # AI가 생성한 문제
    # AI 생성 문제도 이전 문제와 다른 것으로 간주
    reset_feedback_if_problem_changed("ai_generated")
    
    if not st.session_state.api_key:
        st.error("OpenAI API 키를 입력해주세요. 사이드바에서 API 키를 입력할 수 있습니다.")
    else:
        # 문제 생성을 위한 카테고리 선택
        ai_topic_options = [
            "개인/일상생활", "여행/문화", "교육/학업", "사회/이슈", 
            "엔터테인먼트", "비즈니스/업무", "음식/요리", "스포츠/취미"
        ]
        
        ai_topic = st.selectbox("AI가 문제를 생성할 주제를 선택하세요:", ai_topic_options)
        
        # 난이도 선택 세분화 - 깔끔한 2단계 선택 UI
        st.subheader("난이도 선택")
        
        # 난이도 데이터 구성
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
        
        # 선택된 등급에 따른 세부 난이도 선택 (초, 중, 상)
        with col2:
            selected_detail = st.radio(
                "세부 난이도:",
                level_details[st.session_state.selected_level_group],
                horizontal=True,
                key="level_detail",
                index=level_details[st.session_state.selected_level_group].index(st.session_state.selected_level_detail) if st.session_state.selected_level_detail in level_details[st.session_state.selected_level_group] else 1
            )
            st.session_state.selected_level_detail = selected_detail
        
        # 최종 선택된 난이도 값
        final_level = f"{st.session_state.selected_level_group}({st.session_state.selected_level_detail})"
        st.session_state.selected_level_value = final_level
        
        # 선택된 난이도 표시
        st.info(f"현재 선택된 난이도: **{final_level}**")
        
        if st.button("AI 문제 생성하기"):
            with st.spinner("AI가 문제를 생성 중입니다..."):
                try:
                    # OpenAI API를 사용하여 문제 생성
                    client = openai.OpenAI(api_key=st.session_state.api_key)
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
                    
                    # Parse the response
                    ai_problem_text = response.choices[0].message.content
                    
                    # Extract JSON from the response (simple approach)
                    import json
                    import re
                    
                    # Try to extract JSON using regex
                    json_match = re.search(r'```json\n(.*?)\n```', ai_problem_text, re.DOTALL)
                    if json_match:
                        ai_problem_json = json.loads(json_match.group(1))
                    else:
                        # If not in code block, try direct parsing
                        ai_problem_json = json.loads(ai_problem_text)
                    
                    # Set as current problem
                    st.session_state.current_problem = {
                        "category": ai_topic,
                        "question": ai_problem_json.get("question", ""),
                        "context": ai_problem_json.get("context", ""),
                        "example": ai_problem_json.get("example", "")
                    }
                    
                    # Success message
                    st.success("AI가 새로운 문제를 생성했습니다!")
                    
                except Exception as e:
                    st.error(f"문제 생성 중 오류가 발생했습니다: {e}")
        
# Answer section
if st.session_state.current_problem:
    st.header("당신의 답변")
    
    # 현재 선택된 문제 표시
    st.subheader("문제")
    st.write(st.session_state.current_problem["question"])
    
    st.subheader("맥락")
    st.write(st.session_state.current_problem["context"])
    
    if st.session_state.current_problem.get("example"):
        st.subheader("예시 답안")
        st.write(st.session_state.current_problem["example"])
    
    # Input method selection
    input_method = st.radio(
        "답변 입력 방법을 선택하세요:",
        ["직접 텍스트 입력", "파일 업로드", "음성 입력"],
        horizontal=True
    )
    
    user_answer = ""
    
    if input_method == "직접 텍스트 입력":
        # User answer input via text area
        user_answer = st.text_area(
            "답변을 영어로 작성하세요:",
            value=st.session_state.user_answer,
            height=200
        )
    elif input_method == "파일 업로드":
        # File upload for answer
        uploaded_file = st.file_uploader("답변이 담긴 파일을 업로드하세요 (TXT, DOC, DOCX 등)", 
                                        type=["txt", "doc", "docx", "pdf"])
        if uploaded_file is not None:
            try:
                # Read text from the uploaded file
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                user_answer = stringio.read()
                st.write("파일에서 읽은 내용:")
                st.write(user_answer)
            except Exception as e:
                st.error(f"파일 읽기 중 오류가 발생했습니다: {e}")
                st.info("텍스트(.txt) 파일만 지원됩니다. 다른 형식의 파일은 텍스트로 변환 후 업로드해주세요.")
    elif input_method == "음성 입력":
        # Audio recording for answer
        st.write("음성으로 답변 녹음하기")
        st.warning("음성 입력 기능을 사용하려면 마이크 접근 권한을 허용해주세요.")
        
        # Use streamlit experimental audio recorder if available
        audio_input = st.empty()
        audio_input.write("음성 입력 기능은 현재 개발 중입니다. 음성 파일을 업로드하거나 텍스트로 직접 입력해주세요.")
        
        # Placeholder for future audio recording feature
        user_audio = st.file_uploader("또는 오디오 파일을 업로드하세요 (WAV, MP3)", 
                                    type=["wav", "mp3"])
        if user_audio is not None:
            st.audio(user_audio)
            st.info("음성 파일이 업로드되었습니다. 현재 버전에서는 음성-텍스트 변환이 지원되지 않습니다. 추후 업데이트를 기대해주세요.")
    
    # Submit button
    submit = st.button("첨삭 요청하기")
    
    if submit and user_answer:
        # Check if API key is provided
        if not st.session_state.api_key:
            st.error("OpenAI API 키를 입력해주세요. 사이드바에서 API 키를 입력할 수 있습니다.")
        else:
            st.session_state.user_answer = user_answer
            
            with st.spinner("AI가 첨삭 중입니다..."):
                try:
                    # Use the user-provided API key
                    client = openai.OpenAI(api_key=st.session_state.api_key)
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": get_correction_prompt(st.session_state.current_problem, user_answer)}
                        ],
                        temperature=0.7,
                    )
                    
                    # Store the feedback
                    st.session_state.feedback = response.choices[0].message.content
                    
                except Exception as e:
                    st.error(f"API 호출 중 오류가 발생했습니다: {e}")
    
    # Display feedback if available
    if st.session_state.feedback:
        st.header("AI 첨삭 결과")
        st.markdown(st.session_state.feedback)
        
        # Add button to save feedback
        if st.button("결과 저장하기"):
            try:
                # 타임스탬프를 포함한 파일명 생성
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

# Show instruction if API key is not set
if not st.session_state.api_key:
    st.warning("사용하려면 사이드바에 OpenAI API 키를 입력해주세요. API 키는 안전하게 보관되며 현재 세션에서만 사용됩니다.")
