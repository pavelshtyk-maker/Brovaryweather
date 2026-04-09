import requests
import time
import datetime
import pytz
import os

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

kyiv = pytz.timezone('Europe/Kyiv')

# ================= SEND =================
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

# ================= KEYBOARD =================
def main_menu():
    return {
        "keyboard": [
            [{"text": "🌤 Сьогодні"}, {"text": "📅 Завтра"}]
        ],
        "resize_keyboard": True
    }

# ================= WEATHER =================
def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q=Brovary&appid={API_KEY}&units=metric&lang=ua"
    return requests.get(url).json()

def group_by_day(data):
    days = {}

    for t in data["list"]:
        dt = datetime.datetime.strptime(t["dt_txt"], "%Y-%m-%d %H:%M:%S")
        dt = kyiv.localize(dt)
        day = dt.date()

        days.setdefault(day, []).append((dt, t))

    return days

def rain_level(pop):
    if pop < 30:
        return "☁️ без дощу"
    elif pop < 60:
        return "🌦 слабкий"
    elif pop < 85:
        return "🌧 дощ"
    else:
        return "⛈ сильний"

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
        pop = int(t.get("pop", 0) * 100)

        row = f"{dt.strftime('%H:%M')} | {temp}°C | {rain_level(pop)} ({pop}%)"

        if hour < 6:
            parts["🌙 Ніч"].append(row)
        elif hour < 12:
            parts["🌅 Ранок"].append(row)
        elif hour < 18:
            parts["☀️ День"].append(row)
        else:
            parts["🌇 Вечір"].append(row)

    for part, rows in parts.items():
        if rows:
            result += f"\n<b>{part}</b>\n" + "\n".join(rows) + "\n"

    return result

def ai_advice(day_data):
    rain_hours = sum(1 for _, t in day_data if t.get("pop", 0) > 0.4)
    max_temp = max(t["main"]["temp"] for _, t in day_data)

    text = "\n🧠 <b>AI аналіз:</b>\n"

    if rain_hours > 3:
        text += "🌧 Частий дощ протягом дня\n"
    elif rain_hours > 0:
        text += "🌦 Місцями дощ\n"
    else:
        text += "☀️ Сухо\n"

    if max_temp < 5:
        text += "🧥 Холодно\n"
    elif max_temp > 28:
        text += "🔥 Спека\n"

    return text

# ================= DAYS =================
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

# ================= RAIN ALERT SYSTEM =================
last_1h = None
last_10m = None
last_started = None

def rain_alert(data):
    global last_1h, last_10m, last_started

    now = datetime.datetime.now(kyiv)

    for t in data["list"]:
        dt = datetime.datetime.strptime(t["dt_txt"], "%Y-%m-%d %H:%M:%S")
        dt = kyiv.localize(dt)

        diff = (dt - now).total_seconds()
        pop = int(t.get("pop", 0) * 100)

        if pop < 40:
            continue

        # ⚠️ за ~1 год
        if 1800 < diff < 3600:
            if last_1h != dt:
                send(f"⚠️ Дощ приблизно через 1 год (~{dt.strftime('%H:%M')}) {rain_level(pop)}")
                last_1h = dt

        # 🚨 за ~10 хв
        if 0 < diff < 600:
            if last_10m != dt:
                send(f"🚨 ДОЩ ЧЕРЕЗ 10 ХВ! ({dt.strftime('%H:%M')}) {rain_level(pop)}")
                last_10m = dt

        # 🌧 почався
        if -600 < diff < 0:
            if last_started != dt:
                send(f"🌧 Дощ вже йде (~{dt.strftime('%H:%M')}) {rain_level(pop)}")
                last_started = dt

# ================= TELEGRAM =================
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

# ================= MAIN =================
offset = 0
last_21 = None

while True:
    now = datetime.datetime.now(kyiv)

    offset = handle_updates(offset)

    # 🌙 прогноз о 21:00
    if now.hour == 21 and now.minute == 0:
        if last_21 != now.date():
            tomorrow_weather()
            last_21 = now.date()

    # 🌧 дощ система
    data = get_weather()
    rain_alert(data)

    time.sleep(30)
