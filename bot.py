import asyncio
import random
import os
import sys
import pytz
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- ADMIN CONFIG ---
# Replace with your Telegram ID(s)
ADMIN_IDS = [989025647]

def is_admin(user_id):
    return int(user_id) in ADMIN_IDS

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
    await update.message.reply_text("Bot is connected and working")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📶 I'm online! The server hasn't expired yet.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Access denied")
        return
    await update.message.reply_text("✅ You are an admin.")


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Access denied")
        return
    if not os.path.exists(USER_FILE):
        total = 0
    else:
        with open(USER_FILE, "r") as f:
            total = len([l for l in f.read().splitlines() if l.strip()])
    await update.message.reply_text(f"Total users: {total}")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Access denied")
        return

    # Obtain message text to broadcast
    if context.args:
        msg = " ".join(context.args)
    else:
        # if no args, try raw text after command
        text = update.message.text or ""
        parts = text.split(maxsplit=1)
        msg = parts[1] if len(parts) > 1 else None

    if not msg:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    if not os.path.exists(USER_FILE):
        await update.message.reply_text("No users to broadcast to.")
        return

    sent = 0
    failed = 0
    with open(USER_FILE, "r") as f:
        for line in f:
            uid = line.strip()
            if not uid: continue
            try:
                await context.application.bot.send_message(chat_id=uid, text=msg)
                sent += 1
            except Exception:
                failed += 1

    await update.message.reply_text(f"Broadcast complete. Sent: {sent}. Failed: {failed}.")


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Access denied")
        return

    await update.message.reply_text("Restarting bot...")

    # Gracefully stop the application then re-exec the process
    try:
        await context.application.stop()
        await context.application.shutdown()
    except Exception:
        pass

    python = sys.executable
    os.execv(python, [python] + sys.argv)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    # ensure we track every user that interacts
    save_user(chat_id)

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
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # Core handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Admin handlers
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("restart", restart_command))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    asyncio.create_task(scheduler_loop(app))
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())