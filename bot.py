import requests
import time
import datetime
import pytz
import os

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

kyiv = pytz.timezone('Europe/Kyiv')

def send(text, keyboard=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        data["reply_markup"] = keyboard

    requests.post(url, json=data)

def main_menu():
    return {
        "keyboard": [
            ["🌤 Сьогодні", "📅 Завтра"]
        ],
        "resize_keyboard": True
    }

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q=Brovary&appid={API_KEY}&units=metric&lang=ua"
    return requests.get(url).json()

def group_by_day(data):
    days = {}

    for t in data["list"]:
        dt = datetime.datetime.strptime(t["dt_txt"], "%Y-%m-%d %H:%M:%S")
        dt = kyiv.localize(dt)
        day = dt.date()

        if day not in days:
            days[day] = []

        days[day].append((dt, t))

    return days

def format_day(day_data):
    result = ""

    parts = {
        "🌙 Ніч": [],
        "🌅 Ранок": [],
        "☀️ День": [],
        "🌇 Вечір": []
    }

    for dt, t in day_data:
        hour = dt.hour
        temp = round(t["main"]["temp"])
        rain = int(t.get("pop", 0) * 100)

        row = f"{dt.strftime('%H:%M')} | {temp}°C | 🌧 {rain}%"

        if 0 <= hour < 6:
            parts["🌙 Ніч"].append(row)
        elif 6 <= hour < 12:
            parts["🌅 Ранок"].append(row)
        elif 12 <= hour < 18:
            parts["☀️ День"].append(row)
        else:
            parts["🌇 Вечір"].append(row)

    for part, rows in parts.items():
        if rows:
            result += f"\n<b>{part}</b>\n"
            result += "\n".join(rows) + "\n"

    return result

def ai_advice(day_data):
    rain_hours = sum(1 for _, t in day_data if t.get("pop", 0) > 0.3)
    max_temp = max(t["main"]["temp"] for _, t in day_data)
    min_temp = min(t["main"]["temp"] for _, t in day_data)

    advice = "\n🧠 <b>AI аналіз:</b>\n"

    if rain_hours > 2:
        advice += "🌧 Ймовірний дощ — візьми парасолю\n"
    elif rain_hours > 0:
        advice += "🌦 Можливий короткий дощ\n"
    else:
        advice += "☀️ Без опадів\n"

    if max_temp < 5:
        advice += "🧥 Холодно — одягайся тепліше\n"
    elif max_temp > 25:
        advice += "🔥 Спека — пий воду\n"

    return advice

def today_weather():
    data = get_weather()
    days = group_by_day(data)

    today = datetime.datetime.now(kyiv).date()

    if today in days:
        text = "🌤 <b>Сьогодні:</b>\n"
        text += format_day(days[today])
        text += ai_advice(days[today])
        send(text, main_menu())

def tomorrow_weather():
    data = get_weather()
    days = group_by_day(data)

    tomorrow = (datetime.datetime.now(kyiv) + datetime.timedelta(days=1)).date()

    if tomorrow in days:
        text = "📅 <b>Завтра:</b>\n"
        text += format_day(days[tomorrow])
        text += ai_advice(days[tomorrow])
        send(text, main_menu())

def rain_alert(data):
    now = datetime.datetime.now(kyiv)

    for t in data["list"]:
        dt = datetime.datetime.strptime(t["dt_txt"], "%Y-%m-%d %H:%M:%S")
        dt = kyiv.localize(dt)

        if 0 < (dt - now).total_seconds() < 3600:
            rain = int(t.get("pop", 0) * 100)

            if rain > 50:
                send(f"⚠️ Дощ скоро (~{dt.strftime('%H:%M')}) 🌧 {rain}%")
                return

def handle_updates(offset):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}"
    r = requests.get(url).json()

    for u in r["result"]:
        offset = u["update_id"] + 1

        if "message" in u:
            text = u["message"].get("text", "")

            if text == "/start":
                send("👋 Привіт! Обери:", main_menu())

            elif "Сьогодні" in text:
                today_weather()

            elif "Завтра" in text:
                tomorrow_weather()

    return offset

offset = 0
last_21 = None

while True:
    now = datetime.datetime.now(kyiv)

    offset = handle_updates(offset)

    # пуш о 21:00
    if now.hour == 21 and now.minute == 0:
        if last_21 != now.date():
            tomorrow_weather()
            last_21 = now.date()

    # попередження про дощ
    data = get_weather()
    rain_alert(data)

    time.sleep(30)
