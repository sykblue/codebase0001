# 서울 현재 날씨를 OpenWeather에서 받아 보여 주는 파일
# 실행: conda activate camp → python weather.py
import os

import requests
from dotenv import load_dotenv

API = {
    "weather": "https://api.openweathermap.org/data/2.5/weather",  # 🔌 OpenWeather 현재 날씨
}

CITY = {"name": "서울", "lat": 37.5665, "lon": 126.9780}


def main():
    load_dotenv()
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        print(".env에 OPENWEATHER_API_KEY가 없어요. .env.example을 보고 채워 주세요.")
        return

    params = {
        "lat": CITY["lat"],
        "lon": CITY["lon"],
        "appid": key,
        "units": "metric",
        "lang": "kr",
    }
    try:
        res = requests.get(API["weather"], params=params, timeout=10)  # 🔌 API 호출
    except requests.RequestException:
        print("날씨 서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.")
        return

    if res.status_code == 401:
        print("날씨 키가 틀렸거나 아직 켜지지 않았어요(가입 후 최대 2시간).")
        return
    if res.status_code == 404:
        print("그 도시를 찾지 못했어요.")
        return
    if res.status_code == 429:
        print("1분에 너무 많이 불렀어요. 잠시 뒤에 다시 실행해 주세요.")
        return
    if res.status_code != 200:
        print(f"날씨를 불러오지 못했어요. (상태 코드 {res.status_code})")
        return

    data = res.json()
    temp = data["main"]["temp"]  # data["main"]["temp"] = 지금 기온(℃)
    feels = data["main"]["feels_like"]  # data["main"]["feels_like"] = 체감 기온(℃)
    humidity = data["main"]["humidity"]  # data["main"]["humidity"] = 습도(%)
    desc = data["weather"][0]["description"]  # data["weather"][0]["description"] = 날씨 설명

    print(f"📍 {CITY['name']} 현재 날씨")
    print(f"🌡️ 기온 {temp:.1f}℃ (체감 {feels:.1f}℃)")
    print(f"💧 습도 {humidity}%")
    print(f"☁️ {desc}")
    print()
    print("출처: 날씨 - OpenWeather")


if __name__ == "__main__":
    main()
