import requests
import datetime
import time
import os

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

LAT = 50.5119
LON = 30.7905

last_alerts = {}
last_daily_sent = None

def send(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    })

def get_forecast():
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=ua"
    return requests.get(url).json()

def alert_once(key, message):
    global last_alerts
    now = datetime.datetime.now()

    if key in last_alerts:
        if (now - last_alerts[key]).seconds < 7200:
            return

    send(message)
    last_alerts[key] = now

def rain_soon(data):
    for item in data["list"][:4]:
        dt = datetime.datetime.fromtimestamp(item["dt"])
        rain = int(item.get("pop", 0) * 100)

        if rain >= 50:
            alert_once("rain_soon",
                f"🌧️ Скоро дощ\nО {dt.strftime('%H:%M')} (~{rain}%)\n⚠️ Візьми парасолю")
            break

def rain_now(data):
    rain = int(data["list"][0].get("pop", 0) * 100)

    if rain >= 60:
        alert_once("rain_now",
            f"🌧️ Дощ вже починається!\nЙмовірність: {rain}%")

def storm_alert(data):
    for item in data["list"][:3]:
        if "гроза" in item["weather"][0]["description"].lower():
            alert_once("storm", "⚡ Гроза наближається!")
            break

def wind_alert(data):
    for item in data["list"][:3]:
        if item["wind"]["speed"] >= 12:
            alert_once("wind", "💨 Сильний вітер!")
            break

def ai_summary(day_data):
    temps = [x["main"]["temp"] for x in day_data]
    rains = [x.get("pop", 0) * 100 for x in day_data]

    avg_temp = sum(temps) / len(temps)
    max_rain = max(rains)

    text = "\n🧠 AI аналіз:\n"

    if avg_temp < 5:
        text += "🥶 Холодно\n"
    elif avg_temp < 12:
        text += "🧥 Прохолодно\n"
    else:
        text += "👕 Тепло\n"

    if max_rain > 60:
        text += "🌧️ Парасоля обовʼязкова\n"
    elif max_rain > 30:
        text += "🌦️ Можливий дощ\n"
    else:
        text += "☀️ Сухо\n"

    return text

def send_daily():
    global last_daily_sent

    data = get_forecast()
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date()

    text = "🌦️ Погода на завтра (Бровари)\n\n"
    day_data = []

    for item in data["list"]:
        dt = datetime.datetime.fromtimestamp(item["dt"])

        if dt.date() == tomorrow:
            day_data.append(item)
            temp = round(item["main"]["temp"])
            rain = int(item.get("pop", 0) * 100)

            text += f"{dt.strftime('%H:%M')} 🌡 {temp}° 🌧 {rain}%\n"

    text += ai_summary(day_data)

    send(text)
    last_daily_sent = datetime.date.today()

while True:
    now = datetime.datetime.now()
    data = get_forecast()

    if now.hour == 21 and now.minute == 0:
        if last_daily_sent != now.date():
            send_daily()
            time.sleep(60)

    if now.minute % 5 == 0:
        rain_soon(data)
        rain_now(data)
        storm_alert(data)
        wind_alert(data)
        time.sleep(60)

    time.sleep(10)
    
