import os, feedparser, requests, google.generativeai as genai
from datetime import datetime, timedelta

# منابع معتبر اخبار نجومی (RSS رایگان)
FEEDS = [
    "https://www.nasa.gov/news-release/feed/",
    "https://www.esa.int/rssfeed/Our_Activities/Space_Science",
    "https://phys.org/rss-feed/space-news/astronomy/",
    "https://www.space.com/feeds/all",
    "https://skyandtelescope.org/astronomy-news/feed/",
    "https://www.universetoday.com/feed/",
]

# جمع‌آوری اخبار هفته اخیر
one_week_ago = datetime.now() - timedelta(days=7)
articles = []
for url in FEEDS:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            articles.append(f"- {entry.title}\n  {entry.link}\n  خلاصه: {entry.get('summary', '')[:300]}")
    except: pass

news_text = "\n\n".join(articles[:60])

# فراخوانی Gemini برای تحلیل و انتخاب جذاب‌ترین‌ها
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

prompt = f"""تو دستیار یک یوتیوبر ایرانی هستی که در حوزه نجوم و کهکشان‌ها ویدیو می‌سازد.
از بین اخبار زیر، ۵ خبر «جذاب‌ترین، عجیب‌ترین و جدیدترین» درباره کهکشان‌ها، سیاه‌چاله‌ها،
اخترشناسی و کیهان‌شناسی را انتخاب کن.

معیارهای انتخاب:
- تازگی و جذابیت بصری (پتانسیل تصویری خوب برای ویدیو)
- عجیب یا خلاف انتظار بودن
- قابلیت روایت داستانی برای مخاطب فارسی‌زبان

خروجی به فارسی، در قالب زیر باشد:

🌌 *گزارش هفتگی نجوم*

*۱. [عنوان جذاب فارسی]*
📌 خلاصه: [۳-۴ خط]
🎬 چرا برای ویدیو خوبه: [۱-۲ خط پیشنهاد زاویه دید]
🔗 [لینک منبع]

(همین ساختار برای ۵ خبر)

اخبار خام:
{news_text}
"""

response = model.generate_content(prompt)
report = response.text

# ارسال به تلگرام
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# تلگرام محدودیت ۴۰۹۶ کاراکتری داره، پیام رو تکه‌تکه می‌فرستیم
for i in range(0, len(report), 4000):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": report[i:i+4000], "parse_mode": "Markdown"}
    )

print("✅ گزارش ارسال شد")
