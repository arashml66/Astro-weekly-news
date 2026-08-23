import os
import requests
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

client = genai.Client(api_key=GEMINI_API_KEY)

prompt = """
جدیدترین، عجیب‌ترین و جذاب‌ترین اخبار مربوط به کهکشان‌ها و اکتشافات نجومی
در یک هفته اخیر را جست‌وجو کن. ۵ خبر برتر را به فارسی، به شکل لیست شماره‌دار،
هرکدام با یک عنوان جذاب و ۲-۳ جمله توضیح و لینک منبع خلاصه کن.
مناسب برای انتخاب موضوع ویدیوی یوتیوب نجوم باشد.
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    ),
)

report_text = response.text

# ارسال به تلگرام (تلگرام محدودیت طول پیام داره، پس اگه طولانی بود می‌شکنیمش)
def send_telegram(text):
    max_len = 4000
    for i in range(0, len(text), max_len):
        chunk = text[i:i+max_len]
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": chunk}
        )

send_telegram("🌌 گزارش هفتگی اخبار کهکشان‌ها:\n\n" + report_text)
