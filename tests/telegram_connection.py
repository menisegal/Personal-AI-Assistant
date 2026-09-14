import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID", "0"))

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != MY_TELEGRAM_USER_ID:
        return

    text_received = update.message.text
    print(text_received)
    await update.message.reply_text(f"📢 התקבל בהצלחה ב-Windows! שלחת: {text_received}")

if __name__ == "__main__":
    print("🤖 waiting for messages")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))
    app.run_polling()