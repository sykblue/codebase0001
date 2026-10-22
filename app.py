# 도시를 고르면 OpenWeather 현재 날씨를 웹 화면으로 보여 주는 파일
# 실행: conda activate camp → streamlit run app.py
import os

import requests
import streamlit as st
from dotenv import load_dotenv

API = {
    "weather": "https://api.openweathermap.org/data/2.5/weather",  # 🔌 OpenWeather 현재 날씨
}

CITIES = {
    "서울": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014),
    "인천": (37.4563, 126.7052),
    "광주": (35.1595, 126.8526),
    "대전": (36.3504, 127.3845),
    "제주": (33.4996, 126.5312),
}

load_dotenv()


@st.cache_data(ttl=600)
def get_weather(lat, lon):
    """날씨 데이터와 에러 문구 중 하나를 돌려준다. (화면에 키·주소를 보여 주지 않으려고 문구만 돌려줌)"""
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        return None, ".env에 OPENWEATHER_API_KEY가 없어요. .env.example을 보고 채워 주세요."

    params = {"lat": lat, "lon": lon, "appid": key, "units": "metric", "lang": "kr"}
    try:
        res = requests.get(API["weather"], params=params, timeout=10)  # 🔌 API 호출
    except requests.RequestException:
        return None, "날씨 서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요."

    if res.status_code == 401:
        return None, "날씨 키가 틀렸거나 아직 켜지지 않았어요(가입 후 최대 2시간)."
    if res.status_code == 404:
        return None, "그 도시를 찾지 못했어요."
    if res.status_code == 429:
        return None, "1분에 너무 많이 불렀어요. 잠시 뒤에 다시 시도해 주세요."
    if res.status_code != 200:
        return None, f"날씨를 불러오지 못했어요. (상태 코드 {res.status_code})"
    return res.json(), None


st.set_page_config(page_title="오늘 날씨", page_icon="🌤️")
st.title("🌤️ 오늘 날씨")

city = st.selectbox("도시를 골라 주세요", list(CITIES))
if st.button("새로 불러오기"):
    st.cache_data.clear()

data, error = get_weather(*CITIES[city])
if error:
    st.error(error)
else:
    temp = data["main"]["temp"]  # data["main"]["temp"] = 지금 기온(℃)
    feels = data["main"]["feels_like"]  # data["main"]["feels_like"] = 체감 기온(℃)
    humidity = data["main"]["humidity"]  # data["main"]["humidity"] = 습도(%)
    desc = data["weather"][0]["description"]  # data["weather"][0]["description"] = 날씨 설명

    st.subheader(f"📍 {city} · {desc}")
    col1, col2, col3 = st.columns(3)
    col1.metric("기온", f"{temp:.1f}℃")
    col2.metric("체감", f"{feels:.1f}℃")
    col3.metric("습도", f"{humidity}%")

st.divider()
st.caption("🔌 이 화면이 쓰는 API: OpenWeather 현재 날씨 (10분마다 새로 받아요)")
st.caption("출처: 날씨 - OpenWeather")
