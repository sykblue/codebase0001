# 제미나이(Gemini) API로 대화하는 챗봇 웹 화면. 무료 등급 안에서만 쓰도록 하루 사용량에 제한을 건다.
# 실행: conda activate camp → streamlit run chatbot_app.py
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

MODEL = "gemini-2.5-flash-lite"  # 무료 등급에서 쓸 수 있고, 유료로 넘어가도 가장 싼 모델

API = {
    "chat": f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",  # 🔌 Gemini 답변 만들기
}

# 💸 과금 방지 제한 — 숫자를 키우기 전에 11_제미나이_API_요금.md를 먼저 볼 것
LIMITS = {
    "daily_requests": 50,       # 하루에 보낼 수 있는 질문 수
    "daily_budget_usd": 0.05,   # 하루 예상 비용 상한 (유료 단가로 계산, 약 70원)
    "max_input_chars": 1000,    # 질문 한 번의 최대 글자 수
    "max_output_tokens": 800,   # 답변 한 번의 최대 길이
    "history_turns": 6,         # 이전 대화를 몇 번 주고받은 것까지 함께 보낼지 (길수록 입력 토큰이 늘어남)
}

PRICE_PER_1M = {"input": 0.10, "output": 0.40}  # 2.5 Flash-Lite 유료 단가 (USD, 2026-10-19 기준)

SYSTEM_PROMPT = "너는 친절한 한국어 도우미야. 답은 짧고 쉽게 해 줘."

ERROR_CODES = {
    400: "요청이 잘못됐어요. 키가 틀렸거나 지원하지 않는 지역일 수 있어요.",
    401: "제미나이 키가 틀렸어요. .env의 GEMINI_API_KEY를 확인해 주세요.",
    402: "선불 잔액이 0원이에요. 결제 계정이 연결돼 있다는 뜻이니 AI Studio 요금제를 확인해 주세요.",
    403: "제미나이 키에 권한이 없어요. AI Studio에서 키를 다시 확인해 주세요.",
    404: f"{MODEL} 모델을 찾지 못했어요.",
    429: "무료 사용량을 다 썼어요. 1분 뒤나 내일 다시 시도해 주세요. (무료 등급이라 돈은 나가지 않아요)",
}

USAGE_FILE = Path(__file__).with_name(".gemini_usage.json")  # 오늘 사용량을 적어 두는 파일 (새로고침해도 유지)
KST = timezone(timedelta(hours=9))

load_dotenv()


def today():
    return datetime.now(KST).strftime("%Y-%m-%d")


def load_usage():
    """오늘 사용량을 읽는다. 날짜가 바뀌었으면 0부터 다시 센다."""
    empty = {"date": today(), "requests": 0, "input_tokens": 0, "output_tokens": 0}
    try:
        usage = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty
    return usage if usage.get("date") == today() else empty


def save_usage(usage):
    USAGE_FILE.write_text(json.dumps(usage), encoding="utf-8")


def cost_usd(usage):
    return (usage["input_tokens"] * PRICE_PER_1M["input"] + usage["output_tokens"] * PRICE_PER_1M["output"]) / 1_000_000


def limit_message(usage):
    """제한에 걸렸으면 이유 문구를, 아니면 None을 돌려준다."""
    if usage["requests"] >= LIMITS["daily_requests"]:
        return f"오늘 질문 {LIMITS['daily_requests']}번을 다 썼어요. 내일 다시 써 주세요."
    if cost_usd(usage) >= LIMITS["daily_budget_usd"]:
        return f"오늘 예상 비용 상한(${LIMITS['daily_budget_usd']})에 닿았어요. 내일 다시 써 주세요."
    return None


# 대화마다 내용이 달라 같은 요청이 반복되지 않으므로 @st.cache_data를 붙이지 않는다.
# 대신 질문을 보낼 때만 부르고, 하루 횟수·비용 제한으로 호출 수를 막는다.
def ask_gemini(messages):
    """답변 문자열과 토큰 사용량, 에러 문구를 돌려준다. (화면에 키·헤더를 보여 주지 않으려고 문구만 돌려줌)"""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None, None, ".env에 GEMINI_API_KEY가 없어요. .env.example을 보고 채워 주세요."

    recent = messages[-(LIMITS["history_turns"] * 2 + 1):]  # 마지막 질문 + 이전 대화 몇 번만
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in recent
        ],
        "generationConfig": {
            "maxOutputTokens": LIMITS["max_output_tokens"],
            "thinkingConfig": {"thinkingBudget": 0},  # '생각' 토큰도 출력 요금이라 끈다
        },
    }
    headers = {"x-goog-api-key": key}  # 키를 주소에 넣지 않고 헤더로 보낸다
    try:
        res = requests.post(API["chat"], headers=headers, json=body, timeout=30)  # 🔌 API 호출
        data = res.json()
    except requests.RequestException:
        return None, None, "제미나이 서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요."
    except ValueError:
        return None, None, f"답변을 받지 못했어요. (상태 코드 {res.status_code})"

    if res.status_code != 200:
        return None, None, ERROR_CODES.get(res.status_code, f"답변을 받지 못했어요. (상태 코드 {res.status_code})")

    meta = data.get("usageMetadata", {})
    tokens = {
        "input": meta.get("promptTokenCount", 0),  # data["usageMetadata"]["promptTokenCount"] = 보낸 토큰 수
        "output": meta.get("candidatesTokenCount", 0) + meta.get("thoughtsTokenCount", 0),  # 답변 + 생각 토큰 수
    }
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]  # data["candidates"][0]["content"]["parts"][0]["text"] = 답변
    except (KeyError, IndexError):
        return None, tokens, "답변이 비어 있어요. 안전 필터에 걸렸을 수 있으니 질문을 바꿔 주세요."
    return text, tokens, None


st.set_page_config(page_title="제미나이 챗봇", page_icon="🤖")
st.title("🤖 제미나이 챗봇")
st.caption(f"모델: {MODEL} · 무료 등급 안에서만 쓰도록 하루 사용량을 제한했어요")

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "user" 또는 "assistant", "content": "..."}]

usage = load_usage()

with st.sidebar:
    st.subheader("💸 오늘 사용량")
    st.progress(min(usage["requests"] / LIMITS["daily_requests"], 1.0))
    st.write(f"질문 {usage['requests']} / {LIMITS['daily_requests']}번")
    st.write(f"토큰 입력 {usage['input_tokens']:,} · 출력 {usage['output_tokens']:,}")
    st.write(f"유료였다면 약 ${cost_usd(usage):.4f} / 상한 ${LIMITS['daily_budget_usd']}")
    st.caption("결제 계정을 연결하지 않은 무료 등급이면 실제로 나가는 돈은 0원이에요.")
    if st.button("대화 지우기"):
        st.session_state.messages = []
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

blocked = limit_message(usage)
if blocked:
    st.warning(blocked)

prompt = st.chat_input("메시지를 입력하세요", max_chars=LIMITS["max_input_chars"], disabled=bool(blocked))
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    usage["requests"] += 1  # 실패해도 한 번으로 센다 (보수적으로)
    save_usage(usage)

    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            answer, tokens, error = ask_gemini(st.session_state.messages)
        if tokens:
            usage["input_tokens"] += tokens["input"]
            usage["output_tokens"] += tokens["output"]
            save_usage(usage)
        if error:
            st.error(error)
            st.session_state.messages.pop()  # 답을 못 받은 질문은 대화에서 뺀다
        else:
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
    if not error:
        st.rerun()  # 사이드바 사용량을 바로 새 숫자로 (에러일 땐 에러 문구가 사라지지 않게 그대로 둔다)

st.divider()
st.caption("🔌 이 화면이 쓰는 API: Google Gemini API generateContent (질문을 보낼 때만 불러요)")
st.caption("출처: 답변 - Google Gemini")
