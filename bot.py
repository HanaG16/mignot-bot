import os
import random
import logging
from datetime import datetime, timedelta
from flask import Flask, request
import requests as req

logging.basicConfig(level=logging.INFO)

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://mignot-bot.onrender.com/webhook"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_FOLDER = "bot_records"
USER_FILE = os.path.join(DATA_FOLDER, "users.txt")
DATA_FILE = os.path.join(DATA_FOLDER, "productivity_log.txt")

# --- ADMIN ---
ADMIN_IDS = [989025647]
def is_admin(uid): return int(uid) in ADMIN_IDS

# --- STORAGE ---
def initialize_storage():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    for f in [USER_FILE, DATA_FILE]:
        if not os.path.exists(f):
            open(f, "a").close()

def save_user(chat_id):
    with open(USER_FILE, "r") as f:
        users = f.read().splitlines()
    if str(chat_id) not in users:
        with open(USER_FILE, "a") as f:
            f.write(f"{chat_id}\n")

def get_all_users():
    if not os.path.exists(USER_FILE): return []
    with open(USER_FILE, "r") as f:
        return [l.strip() for l in f.read().splitlines() if l.strip()]

# --- TELEGRAM HELPER ---
def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if keyboard:
        payload["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }
    try:
        req.post(f"{API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Failed to send to {chat_id}: {e}")

MAIN_KEYBOARD = [
    ["Are you feeling discouraged? 😔"],
    ["Medical Words 🩺"],
    ["Weekly Report 📊"]
]

# --- CONTENT ---
med_facts = [
    {"term": "Idiopathic", "def": "A condition with an unknown cause."},
    {"term": "Hematopoiesis", "def": "The formation of blood cells."},
    {"term": "Homeostasis", "def": "Stable internal environment."},
    {"term": "Anaphylaxis", "def": "A severe allergic reaction."},
    {"term": "Tachycardia", "def": "Abnormally rapid heart rate."},
    {"term": "Bradycardia", "def": "Abnormally slow heart rate."},
    {"term": "Dyspnea", "def": "Difficulty or labored breathing."},
    {"term": "Edema", "def": "Swelling caused by fluid in tissues."},
    {"term": "Pathogen", "def": "A microorganism that causes disease."},
    {"term": "Prognosis", "def": "The likely course of a disease."}
]

motivational_quotes = [
    {"quote": "The way to get started is to quit talking and begin doing.",
     "tip": "💡 Pick ONE task right now and do it for just 5 minutes. Momentum builds itself."},
    {"quote": "Don't stop when you're tired. Stop when you're done.",
     "tip": "💡 Take a 10-minute walk, drink water, then return. Your brain needs oxygen, not a break."},
    {"quote": "The pain you feel today will be the strength you feel tomorrow.",
     "tip": "💡 Write down 3 things you accomplished today, no matter how small. Progress is progress."},
    {"quote": "You didn't come this far to only come this far.",
     "tip": "💡 Remind yourself WHY you started medicine. Reconnect with your purpose."},
    {"quote": "Success is the sum of small efforts repeated day in and day out.",
     "tip": "💡 Study for 25 minutes, rest for 5. The Pomodoro technique beats marathon sessions."},
    {"quote": "Believe you can and you're halfway there.",
     "tip": "💡 Replace 'I can't do this' with 'I can't do this YET.' Growth mindset changes everything."},
    {"quote": "Hard days are the best because that's when champions are made.",
     "tip": "💡 Talk to a classmate or friend. You're not alone — everyone struggles sometimes."},
    {"quote": "Your limitation is only your imagination.",
     "tip": "💡 Struggling with a topic? Try teaching it out loud to yourself. It reveals gaps fast."},
    {"quote": "Dream it. Wish it. Do it.",
     "tip": "💡 Set a specific goal for tomorrow night before you sleep. Vague goals don't get done."},
    {"quote": "Great doctors were once struggling students. Keep going.",
     "tip": "💡 Sleep at least 7 hours. Memory consolidation happens at night — rest is studying too."},
]

# --- WEEKLY STATS ---
def get_weekly_stats(chat_id):
    if not os.path.exists(DATA_FILE):
        return "No data yet!"
    today = datetime.now().date()
    seven_days_ago = datetime.now() - timedelta(days=7)
    day_map = {}
    with open(DATA_FILE, "r") as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 3 and parts[0] == str(chat_id):
                log_date = datetime.strptime(parts[1], '%Y-%m-%d').date()
                if datetime.combine(log_date, datetime.min.time()) > seven_days_ago:
                    day_map[log_date] = parts[2]
    yes_count = sum(1 for v in day_map.values() if v == "yes")
    no_count  = sum(1 for v in day_map.values() if v == "no")
    total = yes_count + no_count
    if total == 0:
        return "No logs for the past 7 days. Start today! 💪"
    day_row = ""
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        if d not in day_map: day_row += "⬜"
        elif day_map[d] == "yes": day_row += "🟩"
        else: day_row += "🟥"
    streak = 0
    for i in range(0, 7):
        d = today - timedelta(days=i)
        if day_map.get(d) == "yes": streak += 1
        else: break
    if yes_count == 7:   badge = "🏆 LEGEND — Perfect Week!"
    elif yes_count >= 5: badge = "🥇 Gold — Outstanding!"
    elif yes_count >= 4: badge = "🥈 Silver — Great effort!"
    elif yes_count >= 2: badge = "🥉 Bronze — Keep building!"
    else:                badge = "🌱 Beginner — Every expert started here!"
    pct = int((yes_count / total) * 100)
    bar = "🟦" * int(pct / 10) + "⬜" * (10 - int(pct / 10))
    return (
        f"📊 *Weekly Productivity Report*\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"📅 *Last 7 Days:*\nMon▸Tue▸Wed▸Thu▸Fri▸Sat▸Sun\n{day_row}\n"
        f"🟩 = Yes   🟥 = No   ⬜ = No log\n\n"
        f"✅ Productive: *{yes_count}* days\n❌ Off days: *{no_count}* days\n"
        f"📈 Score: *{pct}%*\n{bar}\n\n"
        f"🔥 Current Streak: *{streak} day{'s' if streak != 1 else ''}*\n\n"
        f"🏅 *Badge:* {badge}\n\n"
        f"━━━━━━━━━━━━━━━━\n_Keep logging daily to grow your streak!_ 💪"
    )

# --- MESSAGE HANDLER ---
def handle_update(data):
    msg = data.get("message", {})
    if not msg: return
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    save_user(chat_id)

    if text == "/start":
        send_message(chat_id,
            "👋 *Hello Mignot!*\n\n"
            "This bot is a gift from your lovely friend☺️. I know you are already crushing it but it is the only free gift that I can give. "
            "Why?, well... It is because I am kind and smart and strong and lovely😎.\n\n"
            "🩺 *Morning:* Medical facts & quotes at 8:30 AM.\n"
            "🌙 *Evening:* Productivity check at 9:30 PM.\n"
            "📊 *Weekly:* Check your consistency anytime with the button below.\n\n"
            "The system is now *Active*. Please don't take it for granted—it's made with love! ❤️",
            keyboard=MAIN_KEYBOARD
        )
    elif text == "/ping":
        send_message(chat_id, "📶 I'm online! The server hasn't expired yet.")
    elif text == "/id":
        send_message(chat_id, f"Your Telegram ID: `{chat_id}`")
    elif text == "/admin":
        if is_admin(chat_id):
            send_message(chat_id, "✅ You are an admin.")
        else:
            send_message(chat_id, "Access denied.")
    elif text == "/stats":
        if is_admin(chat_id):
            send_message(chat_id, f"Total users: {len(get_all_users())}")
        else:
            send_message(chat_id, "Access denied.")
    elif text.startswith("/broadcast "):
        if is_admin(chat_id):
            msg_text = text[len("/broadcast "):]
            sent = failed = 0
            for uid in get_all_users():
                try:
                    req.post(f"{API}/sendMessage",
                             json={"chat_id": uid, "text": msg_text},
                             timeout=10)
                    sent += 1
                except:
                    failed += 1
            send_message(chat_id, f"Broadcast complete. Sent: {sent}. Failed: {failed}.")
        else:
            send_message(chat_id, "Access denied.")
    elif text == "Are you feeling discouraged? 😔":
        item = random.choice(motivational_quotes)
        send_message(chat_id,
            f"✨ _{item['quote']}_\n\n{item['tip']}",
            keyboard=MAIN_KEYBOARD)
    elif text == "Medical Words 🩺":
        fact = random.choice(med_facts)
        send_message(chat_id,
            f"🧠 *{fact['term']}*: {fact['def']}",
            keyboard=MAIN_KEYBOARD)
    elif text == "Weekly Report 📊":
        send_message(chat_id, get_weekly_stats(chat_id), keyboard=MAIN_KEYBOARD)
    elif text.lower() in ["yes", "no"]:
        with open(DATA_FILE, "a") as f:
            f.write(f"{chat_id},{datetime.now().strftime('%Y-%m-%d')},{text.lower()}\n")
        send_message(chat_id, "🔥 Recorded! Keep pushing.", keyboard=MAIN_KEYBOARD)
    else:
        send_message(chat_id, "Choose an option below 👇", keyboard=MAIN_KEYBOARD)

# --- FLASK ---
initialize_storage()
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "mignot-bot is running! ❤️"

@flask_app.route("/health")
def health():
    return "OK"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    handle_update(data)
    return "OK"

@flask_app.route("/morning")
def morning():
    users = get_all_users()
    for uid in users:
        fact = random.choice(med_facts)
        send_message(uid, f"☀️ Good morning! Today's word:\n*{fact['term']}*: {fact['def']}")
    return f"Morning sent to {len(users)} users"

@flask_app.route("/evening")
def evening():
    users = get_all_users()
    for uid in users:
        send_message(uid, "🌙 Was your day productive today? (Yes/No)")
    return f"Evening sent to {len(users)} users"

# --- SET WEBHOOK ---
def set_webhook():
    res = req.get(f"{API}/setWebhook?url={WEBHOOK_URL}")
    logging.info(f"Webhook set: {res.json()}")

set_webhook()

if __name__ == '__main__':
    flask_app.run(host="0.0.0.0", port=8080)
