import asyncio
import random
import os
import pytz
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = os.environ.get("TOKEN")
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
    {"term": "Anaphylaxis", "def": "A severe allergic reaction."}
]

motivational_quotes = [
    "The way to get started is to quit talking and begin doing.",
    "Don't stop when you're tired. Stop when you're done.",
    "The pain you feel today will be the strength you feel tomorrow."
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

def get_weekly_stats(chat_id):
    if not os.path.exists(DATA_FILE): return "No data yet!"
    yes_count = 0
    no_count = 0
    seven_days_ago = datetime.now() - timedelta(days=7)

    with open(DATA_FILE, "r") as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 3 and parts[0] == str(chat_id):
                log_date = datetime.strptime(parts[1], '%Y-%m-%d')
                if log_date > seven_days_ago:
                    if parts[2] == "yes": yes_count += 1
                    else: no_count += 1

    total = yes_count + no_count
    if total == 0: return "No logs for the past 7 days. Start today! 💪"

    bar = "✅" * yes_count + "❌" * no_count
    return f"📊 *Weekly Productivity*\n\nYes: {yes_count}\nNo: {no_count}\n\nProgress: {bar}\nKeep going, Doctor!"

# --- HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_chat.id)
    welcome_text = (
        "👋 *Hello Mignot!*\n\n"
        "This bot is a gift from your lovely friend☺️. I know you are already crushing it but it is the only free gift that I can give. "
        "Why?, well... It is because I am kind and smart and strong and lovely😎.\n\n"
        "🩺 *Morning:* Medical facts & quotes at 8:30 AM.\n"
        "🌙 *Evening:* Productivity check at 9:30 PM.\n"
        "📊 *Weekly:* Check your consistency anytime with the button below.\n\n"
        "The system is now *Active*. Please don't take it for granted—it's made with love! ❤️"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard, parse_mode='Markdown')

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📶 I'm online! The server hasn't expired yet.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    if text == "Are you feeling discouraged? 😔":
        await update.message.reply_text(f"✨ _{random.choice(motivational_quotes)}_", parse_mode='Markdown')
    elif text == "Medical Words 🩺":
        fact = random.choice(med_facts)
        await update.message.reply_text(f"🧠 *{fact['term']}*: {fact['def']}", parse_mode='Markdown')
    elif text == "Weekly Report 📊":
        stats = get_weekly_stats(chat_id)
        await update.message.reply_text(stats, parse_mode='Markdown')
    elif text.lower() in ["yes", "no"]:
        with open(DATA_FILE, "a") as f:
            f.write(f"{chat_id},{datetime.now().strftime('%Y-%m-%d')},{text.lower()}\n")
        await update.message.reply_text("🔥 Recorded! Keep pushing.", reply_markup=main_menu_keyboard)

# --- SCHEDULER ---
async def scheduler_loop(app):
    ethiopia_tz = pytz.timezone('Africa/Addis_Ababa')

    last_morning_sent = None
    last_evening_sent = None

    while True:
        now = datetime.now(ethiopia_tz)
        today = now.date()

        if now.hour == 8 and now.minute >= 30 and last_morning_sent != today:
            last_morning_sent = today
            for uid in open(USER_FILE).read().splitlines():
                fact = random.choice(med_facts)
                try:
                    await app.bot.send_message(
                        chat_id=uid,
                        text=f"☀️ Good morning! Today's word:\n*{fact['term']}*: {fact['def']}",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"Failed to send morning message to {uid}: {e}")

        if now.hour == 21 and now.minute >= 30 and last_evening_sent != today:
            last_evening_sent = today
            for uid in open(USER_FILE).read().splitlines():
                try:
                    await app.bot.send_message(
                        chat_id=uid,
                        text="🌙 Was your day productive today? (Yes/No)"
                    )
                except Exception as e:
                    print(f"Failed to send evening message to {uid}: {e}")

        await asyncio.sleep(30)

async def main():
    initialize_storage()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await scheduler_loop(app)

if __name__ == '__main__':
    asyncio.run(main())