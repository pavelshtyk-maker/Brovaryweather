import requests
import time
import datetime
import pytz

TOKEN = "ТВОЙ_TOKEN"
CHAT_ID = "444719451"
API_KEY = "ТВОЙ_API_KEY"

def send(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=data)

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q=Brovary&appid={API_KEY}&units=metric&lang=ua"
    return requests.get(url).json()

def weather_now():
    data = get_weather()
    temp = data["list"][0]["main"]["temp"]
    send(f"🌤 Зараз: {temp}°C")

kyiv = pytz.timezone('Europe/Kyiv')

while True:
    now = datetime.datetime.now(kyiv)

    if now.hour == 21 and now.minute == 0:
        send("📅 Прогноз на завтра")
        weather_now()
        time.sleep(60)

    time.sleep(10)
