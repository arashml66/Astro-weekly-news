import os
import html
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from google import genai


# =========================================================
# تنظیمات
# =========================================================

FEEDS = [
    "https://www.nasa.gov/news-release/feed/",
    "https://www.esa.int/rssfeed/Our_Activities/Space_Science",
    "https://phys.org/rss-feed/space-news/astronomy/",
    "https://www.space.com/feeds/all",
    "https://skyandtelescope.org/astronomy-news/feed/",
    "https://www.universetoday.com/feed/",
]

MAX_ARTICLES_PER_FEED = 15
MAX_TOTAL_ARTICLES = 60

# فقط خبرهای نسبتاً جدید را بررسی می‌کنیم
MAX_AGE_DAYS = 10


# =========================================================
# بررسی Secretها
# =========================================================

required_env = [
    "GEMINI_API_KEY",
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
]

for name in required_env:
    if not os.environ.get(name):
        raise RuntimeError(f"Secret مورد نیاز پیدا نشد: {name}")


# =========================================================
# جمع‌آوری اخبار
# =========================================================

def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)

    # حذف ساده HTML
    import re
    text = re.sub(r"<[^>]+>", " ", text)

    # حذف فاصله‌های اضافی
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_entry_date(entry):
    """
    تلاش برای پیدا کردن تاریخ انتشار خبر
    """

    for field in ["published_parsed", "updated_parsed"]:
        value = getattr(entry, field, None)

        if value:
            try:
                from time import mktime
                return datetime.fromtimestamp(
                    mktime(value),
                    tz=timezone.utc
                )
            except Exception:
                pass

    return None


def collect_news():

    articles = []
    seen_links = set()

    now = datetime.now(timezone.utc)
    minimum_date = now - timedelta(days=MAX_AGE_DAYS)

    for feed_url in FEEDS:

        try:
            print(f"Reading: {feed_url}")

            feed = feedparser.parse(feed_url)

            if getattr(feed, "bozo", False):
                print("⚠️ RSS warning:", feed_url)

            for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:

                title = clean_text(
                    getattr(entry, "title", "")
                )

                link = getattr(entry, "link", "")

                summary = clean_text(
                    getattr(entry, "summary", "")
                )

                if not title or not link:
                    continue

                # حذف اخبار تکراری
                if link in seen_links:
                    continue

                # بررسی تاریخ
                published = get_entry_date(entry)

                if published and published < minimum_date:
                    continue

                seen_links.add(link)

                articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:700],
                    "published": (
                        published.isoformat()
                        if published else "unknown"
                    )
                })

        except Exception as e:
            print(f"⚠️ خطا در RSS: {feed_url}")
            print(e)

    # مرتب‌سازی بر اساس تاریخ
    articles.sort(
        key=lambda x: x["published"],
        reverse=True
    )

    return articles[:MAX_TOTAL_ARTICLES]


# =========================================================
# تبدیل اخبار به متن برای Gemini
# =========================================================

articles = collect_news()

if not articles:
    raise RuntimeError(
        "هیچ خبر معتبری از RSSها دریافت نشد."
    )

print(f"✅ تعداد اخبار جمع‌آوری‌شده: {len(articles)}")


news_text_parts = []

for i, article in enumerate(articles, 1):

    news_text_parts.append(
        f"""
خبر {i}
عنوان: {article['title']}
تاریخ: {article['published']}
خلاصه: {article['summary']}
منبع: {article['link']}
"""
    )

news_text = "\n".join(news_text_parts)


# =========================================================
# Gemini
# =========================================================

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


system_instruction = """
تو سردبیر علمی یک کانال یوتیوب فارسی‌زبان در حوزه
نجوم، کیهان‌شناسی، سیاه‌چاله‌ها، کهکشان‌ها، سیارات،
SETI و جستجوی حیات فرازمینی هستی.

وظیفه تو انتخاب بهترین اخبار برای تولید محتوای یوتیوب است.

قوانین:

1. خبرهای تکراری را حذف کن.
2. خبرهایی که صرفاً تبلیغاتی یا کم‌اهمیت هستند حذف کن.
3. خبر علمی را با ادعای علمی اثبات‌نشده اشتباه نگیر.
4. اگر خبر مربوط به حیات فرازمینی یا UFO/UAP است،
   لحن هیجان‌انگیز باشد اما ادعای اثبات‌نشده را حقیقت جلوه نده.
5. تازگی، اهمیت علمی، جذابیت بصری و ظرفیت داستان‌گویی
   را در انتخاب اخبار در نظر بگیر.
6. اخبار را برای مخاطب فارسی‌زبان جذاب کن.
7. عنوان فارسی باید جذاب باشد اما Clickbait دروغین نباشد.
8. منبع اصلی خبر را حفظ کن.
9. اگر اطلاعات یک خبر برای نتیجه‌گیری قطعی کافی نیست،
   صریحاً این موضوع را ذکر کن.
"""


prompt = f"""
از بین اخبار زیر دقیقاً ۵ خبر برتر را انتخاب کن.

اولویت انتخاب:

- اهمیت علمی
- تازگی
- عجیب و غیرمنتظره بودن
- قابلیت ساخت ویدیو
- جذابیت تصویری
- قابلیت روایت داستانی
- ارتباط با کیهان، سیاه‌چاله‌ها، کهکشان‌ها،
  ستاره‌ها، سیارات، حیات فرازمینی و فناوری فضایی

گزارش را به فارسی تولید کن.

ساختار دقیق:

🌌 گزارش هفتگی نجوم

━━━━━━━━━━━━━━

🚀 خبر ۱ — [عنوان جذاب]

📌 خلاصه:
۳ تا ۴ خط توضیح دقیق و قابل فهم.

🔬 اهمیت علمی:
چرا این خبر مهم است؟

🎬 ایده ویدیو:
یک زاویه جذاب برای ساخت ویدیوی یوتیوب پیشنهاد بده.

⚠️ نکته مهم:
اگر ادعا یا نتیجه‌ای هنوز قطعی نیست، توضیح بده.

🔗 منبع:
[URL اصلی]

━━━━━━━━━━━━━━

همین ساختار را برای ۵ خبر ادامه بده.

در پایان:

🔥 بهترین گزینه برای ویدیوی این هفته:
نام خبر + یک دلیل کوتاه

اخبار خام:

{news_text}
"""


try:

    response = client.models.generate_content(
        model="gemini-3.7-flash",
        contents=prompt,
        config={
            "system_instruction": system_instruction,
            "temperature": 0.4,
            "max_output_tokens": 6000,
        },
    )

    report = response.text

except Exception as e:

    raise RuntimeError(
        f"خطا در ارتباط با Gemini: {e}"
    )


if not report:
    raise RuntimeError(
        "Gemini هیچ گزارشی تولید نکرد."
    )


# =========================================================
# Telegram
# =========================================================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def send_telegram_message(text):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    # Telegram محدودیت طول پیام دارد.
    # برای جلوگیری از خراب شدن Markdown،
    # از HTML استفاده نمی‌کنیم و متن ساده می‌فرستیم.

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"Telegram error: {response.text}"
        )


# تقسیم گزارش به قطعات امن
MAX_TELEGRAM_LENGTH = 3900

for start in range(0, len(report), MAX_TELEGRAM_LENGTH):

    chunk = report[
        start:start + MAX_TELEGRAM_LENGTH
    ]

    send_telegram_message(chunk)


print("✅ گزارش با موفقیت به تلگرام ارسال شد.")
