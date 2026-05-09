import asyncio
import random
import os
import json
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- ADMIN CONFIG ---
ADMIN_IDS = [989025647]

def is_admin(user_id):
    return int(user_id) in ADMIN_IDS

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://mignot-bot.onrender.com/webhook"
DATA_FOLDER = "bot_records"
USER_FILE = os.path.join(DATA_FOLDER, "users.txt")
DATA_FILE = os.path.join(DATA_FOLDER, "productivity_log.txt")

# --- INITIALIZE STORAGE ---
def initialize_storage():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    for file in [USER_FILE, DATA_FILE]:
        if not os.path.exists(file):
            open(file, "a").close()

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
    {
        "quote": "The way to get started is to quit talking and begin doing.",
        "tip": "💡 Pick ONE task right now and do it for just 5 minutes. Momentum builds itself."
    },
    {
        "quote": "Don't stop when you're tired. Stop when you're done.",
        "tip": "💡 Take a 10-minute walk, drink water, then return. Your brain needs oxygen, not a break."
    },
    {
        "quote": "The pain you feel today will be the strength you feel tomorrow.",
        "tip": "💡 Write down 3 things you accomplished today, no matter how small. Progress is progress."
    },
    {
        "quote": "You didn't come this far to only come this far.",
        "tip": "💡 Remind yourself WHY you started medicine. Reconnect with your purpose."
    },
    {
        "quote": "Success is the sum of small efforts repeated day in and day out.",
        "tip": "💡 Study for 25 minutes, rest for 5. The Pomodoro technique beats marathon sessions."
    },
    {
        "quote": "Believe you can and you're halfway there.",
        "tip": "💡 Replace 'I can't do this' with 'I can't do this YET.' Growth mindset changes everything."
    },
    {
        "quote": "Hard days are the best because that's when champions are made.",
        "tip": "💡 Talk to a classmate or friend. You're not alone — everyone struggles sometimes."
    },
    {
        "quote": "Your limitation is only your imagination.",
        "tip": "💡 Struggling with a topic? Try teaching it out loud to yourself. It reveals gaps fast."
    },
    {
        "quote": "Dream it. Wish it. Do it.",
        "tip": "💡 Set a specific goal for tomorrow night before you sleep. Vague goals don't get done."
    },
    {
        "quote": "Great doctors were once struggling students. Keep going.",
        "tip": "💡 Sleep at least 7 hours. Memory consolidation happens at night — rest is studying too."
    },
]

main_menu_keyboard = ReplyKeyboardMarkup(
    [["Are you feeling discouraged? 😔"], ["Medical Words 🩺"], ["Weekly Report 📊"]],
    resize_keyboard=True
)

# --- UTILS ---
def save_user(chat_id):
    with open(USER_FILE, "r") as f:
        users = f.read().splitlines()
    if str(chat_id) not in users:
        with open(USER_FILE, "a") as f:
            f.write(f"{chat_id}\n")

def get_all_users():
    if not os.path.exists(USER_FILE):
        return []
    with open(USER_FILE, "r") as f:
        return [l.strip() for l in f.read().splitlines() if l.strip()]

def get_weekly_stats(chat_id):
    if not os.path.exists(DATA_FILE): return "No data yet!"

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
        if d not in day_map:
            day_row += "⬜"
        elif day_map[d] == "yes":
            day_row += "🟩"
        else:
            day_row += "🟥"

    streak = 0
    for i in range(0, 7):
        d = today - timedelta(days=i)
        if day_map.get(d) == "yes":
            streak += 1
        else:
            break

    if yes_count == 7:
        badge = "🏆 LEGEND — Perfect Week!"
    elif yes_count >= 5:
        badge = "🥇 Gold — Outstanding!"
    elif yes_count >= 4:
        badge = "🥈 Silver — Great effort!"
    elif yes_count >= 2:
        badge = "🥉 Bronze — Keep building!"
    else:
        badge = "🌱 Beginner — Every expert started here!"

    pct = int((yes_count / total) * 100)
    filled = int(pct / 10)
    bar = "🟦" * filled + "⬜" * (10 - filled)

    return (
        f"📊 *Weekly Productivity Report*\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"📅 *Last 7 Days:*\n"
        f"Mon▸Tue▸Wed▸Thu▸Fri▸Sat▸Sun\n"
        f"{day_row}\n"
        f"🟩 = Yes   🟥 = No   ⬜ = No log\n\n"
        f"✅ Productive: *{yes_count}* days\n"
        f"❌ Off days:   *{no_count}* days\n"
        f"📈 Score: *{pct}%*\n"
        f"{bar}\n\n"
        f"🔥 Current Streak: *{streak} day{'s' if streak != 1 else ''}*\n\n"
        f"🏅 *Badge:* {badge}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"_Keep logging daily to grow your streak!_ 💪"
    )

# --- BUILD APP ---
initialize_storage()
app = ApplicationBuilder().token(BOT_TOKEN).updater(None).build()

# --- HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_chat.id)
    await update.message.reply_text(
        "👋 *Hello Mignot!*\n\n"
        "This bot is a gift from your lovely friend☺️. I know you are already crushing it but it is the only free gift that I can give. "
        "Why?, well... It is because I am kind and smart and strong and lovely😎.\n\n"
        "🩺 *Morning:* Medical facts & quotes at 8:30 AM.\n"
        "🌙 *Evening:* Productivity check at 9:30 PM.\n"
        "📊 *Weekly:* Check your consistency anytime with the button below.\n\n"
        "The system is now *Active*. Please don't take it for granted—it's made with love! ❤️",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📶 I'm online! The server hasn't expired yet.")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access denied")
        return
    await update.message.reply_text("✅ You are an admin.")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access denied")
        return
    total = len(get_all_users())
    await update.message.reply_text(f"Total users: {total}")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access denied")
        return
    if context.args:
        msg = " ".join(context.args)
    else:
        text = update.message.text or ""
        parts = text.split(maxsplit=1)
        msg = parts[1] if len(parts) > 1 else None
    if not msg:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    sent = failed = 0
    for uid in get_all_users():
        try:
            await context.application.bot.send_message(chat_id=uid, text=msg)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"Broadcast complete. Sent: {sent}. Failed: {failed}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    save_user(chat_id)

    if text == "Are you feeling discouraged? 😔":
        item = random.choice(motivational_quotes)
        await update.message.reply_text(f"✨ _{item['quote']}_\n\n{item['tip']}", parse_mode='Markdown', reply_markup=main_menu_keyboard)
    elif text == "Medical Words 🩺":
        fact = random.choice(med_facts)
        await update.message.reply_text(f"🧠 *{fact['term']}*: {fact['def']}", parse_mode='Markdown', reply_markup=main_menu_keyboard)
    elif text == "Weekly Report 📊":
        stats = get_weekly_stats(chat_id)
        await update.message.reply_text(stats, parse_mode='Markdown', reply_markup=main_menu_keyboard)
    elif text.lower() in ["yes", "no"]:
        with open(DATA_FILE, "a") as f:
            f.write(f"{chat_id},{datetime.now().strftime('%Y-%m-%d')},{text.lower()}\n")
        await update.message.reply_text("🔥 Recorded! Keep pushing.", reply_markup=main_menu_keyboard)
    else:
        await update.message.reply_text("Choose an option below 👇", reply_markup=main_menu_keyboard)

app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("ping", ping_command))
app.add_handler(CommandHandler("admin", admin_command))
app.add_handler(CommandHandler("id", id_command))
app.add_handler(CommandHandler("stats", stats_command))
app.add_handler(CommandHandler("broadcast", broadcast_command))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# --- FLASK APP ---
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
    asyncio.run(process_update(data))
    return "OK"

@flask_app.route("/morning")
def morning():
    asyncio.run(send_morning())
    return "OK"

@flask_app.route("/evening")
def evening():
    asyncio.run(send_evening())
    return "OK"

# --- SCHEDULED MESSAGE FUNCTIONS ---
async def send_morning():
    for uid in get_all_users():
        fact = random.choice(med_facts)
        try:
            await app.bot.send_message(
                chat_id=uid,
                text=f"☀️ Good morning! Today's word:\n*{fact['term']}*: {fact['def']}",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed morning msg to {uid}: {e}")

async def send_evening():
    for uid in get_all_users():
        try:
            await app.bot.send_message(
                chat_id=uid,
                text="🌙 Was your day productive today? (Yes/No)"
            )
        except Exception as e:
            print(f"Failed evening msg to {uid}: {e}")

async def process_update(data):
    update = Update.de_json(data, app.bot)
    await app.initialize()
    await app.process_update(update)

# --- SET WEBHOOK ON STARTUP ---
async def set_webhook():
    await app.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")

if __name__ == '__main__':
    asyncio.run(set_webhook())
    flask_app.run(host="0.0.0.0", port=8080)
