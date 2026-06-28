import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

# 🔑 ключи будут подтягиваться из Render (НЕ вставляем сюда)
TOKEN = os.getenv("TELEGRAM_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🧠 база данных (память + задачи)
conn = sqlite3.connect("assistant.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    content TEXT,
    created_at TEXT
)
""")

conn.commit()

# 💾 сохранить память
def save_memory(user_id, role, content):
    cursor.execute(
        "INSERT INTO memory (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (user_id, role, content, str(datetime.now()))
    )
    conn.commit()

# 📚 получить память
def get_memory(user_id, limit=10):
    cursor.execute(
        "SELECT role, content FROM memory WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

# 🤖 ответ AI
def ask_ai(user_id, text):
    memory = get_memory(user_id)

    messages = [
        {
            "role": "system",
            "content": "Ты личный Telegram ассистент. Помогаешь с задачами, текстами и запоминаешь информацию пользователя."
        }
    ]

    messages += memory
    messages.append({"role": "user", "content": text})

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
    )

    answer = res.choices[0].message.content

    save_memory(user_id, "user", text)
    save_memory(user_id, "assistant", answer)

    return answer

# 📩 обработка сообщений
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.message.chat_id)

    answer = ask_ai(user_id, text)
    await update.message.reply_text(answer)

# 🚀 запуск бота
app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
