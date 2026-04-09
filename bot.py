import requests
import time
import datetime
import pytz
import os

# --- ENV ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

# --- SEND ---
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


# --- КНОПКИ ---
def main_menu():
    return {
        "keyboard": [
            ["🌤 Зараз", "📅 Завтра"],
            ["🔄 Оновити"]
        ],
        "resize_keyboard": True
    }


# --- ПОГОДА ---
def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q=Brovary&appid={API_KEY}&units=metric&lang=ua"
    return requests.get(url).json()


# --- ЗАРАЗ ---
def weather_now():
    data = get_weather()

    temp = round(data["list"][0]["main"]["temp"])
    desc = data["list"][0]["weather"][0]["description"]
    wind = round(data["list"][0]["wind"]["speed"])

    text = (
        f"🌤 <b>Зараз:</b>\n"
        f"🌡 {temp}°C\n"
        f"🌥 {desc}\n"
        f"💨 {wind} м/с"
    )

    send(text, main_menu())


# --- ЗАВТРА ---
def weather_tomorrow():
    data = get_weather()
    result = "📅 <b>Завтра погодинно:</b>\n\n"

    for i in range(8, 16):
        t = data["list"][i]

        time_txt = t["dt_txt"][11:16]
        temp = round(t["main"]["temp"])
        rain = int(t.get("pop", 0) * 100)

        result += f"{time_txt} | {temp}°C | 🌧 {rain}%\n"

    result += ai_advice(data)

    send(result, main_menu())


# --- AI АНАЛІЗ ---
def ai_advice(data):
    text = "\n🧠 <b>AI аналіз:</b>\n"

    rain_detected = False
    wind_detected = False

    for i in range(0, 10):
        rain = int(data["list"][i].get("pop", 0) * 100)
        wind = data["list"][i]["wind"]["speed"]

        if rain > 30:
            rain_detected = True

        if wind > 10:
            wind_detected = True

    if rain_detected:
        text += "☔ Можливий дощ — візьми парасолю\n"
    else:
        text += "☀️ Без опадів — можна гуляти\n"

    if wind_detected:
        text += "💨 Сильний вітер\n"

    return text


# --- PUSH ДОЩ ---
last_rain_alert = None

def rain_alert(data):
    global last_rain_alert

    for i in range(0, 3):
        rain = int(data["list"][i].get("pop", 0) * 100)

        if rain > 50:
            now_hour = datetime.datetime.now().hour

            if last_rain_alert != now_hour:
                send("🌧 Дощ скоро (~1-2 години)")
                last_rain_alert = now_hour
            return


# --- ОБРОБКА КОМАНД ---
last_update_id = None

def check_messages():
    global last_update_id

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    data = requests.get(url).json()

    if "result" not in data:
        return

    for item in data["result"]:
        update_id = item["update_id"]

        if last_update_id is not None and update_id <= last_update_id:
            continue

        last_update_id = update_id

        if "message" in item:
            text = item["message"].get("text", "")

            if text == "/start":
                send("👋 Бот погоди Бровари\n\nОбери дію:", main_menu())

            elif text == "🌤 Зараз":
                weather_now()

            elif text == "📅 Завтра":
                weather_tomorrow()

            elif text == "🔄 Оновити":
                weather_now()


# --- TIMEZONE ---
kyiv = pytz.timezone('Europe/Kyiv')

last_morning = None
last_evening = None


# --- MAIN LOOP ---
while True:
    now = datetime.datetime.now(kyiv)
    data = get_weather()

    check_messages()

    # 🌅 08:00
    if now.hour == 8 and now.minute == 0:
        if last_morning != now.date():
            send("🌅 Доброго ранку!\n\nПрогноз на сьогодні:")
            weather_now()
            last_morning = now.date()
            time.sleep(60)

    # 🌙 21:00
    if now.hour == 21 and now.minute == 0:
        if last_evening != now.date():
            send("🌙 Прогноз на завтра:")
            weather_tomorrow()
            last_evening = now.date()
            time.sleep(60)

    # 🌧 перевірка дощу
    if now.minute % 10 == 0:
        rain_alert(data)
        time.sleep(60)

    time.sleep(10)
