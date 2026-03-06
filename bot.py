import telebot
import sqlite3
import os
import time
import requests
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

user_modes = {}
last_messages = {}

pending_edit = {}
generation_lock = {}

# база данных
db = sqlite3.connect("database.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
username TEXT,
tokens INTEGER,
requests INTEGER,
referrer INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory(
user_id INTEGER PRIMARY KEY,
history TEXT
)
""")

db.commit()


# регистрация пользователя
def register_user(user, ref=None):

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    exists = cursor.fetchone()

    if exists:
        return

    username = user.username if user.username else "none"

    referrer = None

    if ref and ref != user.id:

        cursor.execute("SELECT user_id FROM users WHERE user_id=?", (ref,))
        ref_exists = cursor.fetchone()

        if ref_exists:

            referrer = ref

            cursor.execute(
                "UPDATE users SET tokens = tokens + 15 WHERE user_id=?",
                (ref,)
            )

    cursor.execute(
        "INSERT INTO users VALUES(?,?,?,?,?)",
        (user.id, username, 50, 0, referrer)
    )

    db.commit()


# память GPT
def get_memory(user_id):

    cursor.execute("SELECT history FROM memory WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    if data is None:

        history = [
            {"role": "system", "content": "Ты дружелюбный умный AI помощник."}
        ]

        cursor.execute(
            "INSERT INTO memory VALUES(?,?)",
            (user_id, json.dumps(history))
        )

        db.commit()

        return history

    return json.loads(data[0])


def save_memory(user_id, history):

    cursor.execute(
        "UPDATE memory SET history=? WHERE user_id=?",
        (json.dumps(history), user_id)
    )

    db.commit()


# GPT функция
def ask_gpt(user_id, text):

    cursor.execute(
        "SELECT tokens FROM users WHERE user_id=?",
        (user_id,)
    )

    tokens = cursor.fetchone()[0]

    if tokens <= 0:
        return "❌ У вас закончились токены."

    history = get_memory(user_id)

    history.append({
        "role": "user",
        "content": text
    })

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": history,
        "temperature": 0.7
    }

    r = requests.post(url, headers=headers, json=data)

    answer = r.json()["choices"][0]["message"]["content"]

    history.append({
        "role": "assistant",
        "content": answer
    })

    if len(history) > 20:
        history = history[-20:]

    save_memory(user_id, history)

    cursor.execute(
        "UPDATE users SET tokens = tokens - 1, requests = requests + 1 WHERE user_id=?",
        (user_id,)
    )

    db.commit()

    return answer


# генерация изображения
def generate_flux(prompt):

    url = "https://api.bfl.ml/v1/flux"

    headers = {
        "Authorization": "Bearer " + os.getenv("FLUX_API_KEY"),
        "Content-Type": "application/json"
    }

    data = {
        "prompt": prompt,
        "aspect_ratio": "1:1"
    }

    r = requests.post(url, headers=headers, json=data)
    result = r.json()

    return result["image_url"]


# редактирование изображения
def edit_image(image_url, prompt):

    url = "https://api.bfl.ml/v1/edit"

    headers = {
        "Authorization": "Bearer " + os.getenv("FLUX_API_KEY"),
        "Content-Type": "application/json"
    }

    data = {
        "image": image_url,
        "prompt": prompt
    }

    r = requests.post(url, headers=headers, json=data)
    result = r.json()

    return result["image_url"]


# удаление старого сообщения
def clean(chat_id):

    if chat_id in last_messages:

        try:
            bot.delete_message(chat_id, last_messages[chat_id])
        except:
            pass


# отправка нового сообщения
def send(chat_id, text, keyboard=None):

    clean(chat_id)

    msg = bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard
    )

    last_messages[chat_id] = msg.message_id


# главное меню
def main_menu():

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("🥷 Убийца фотошопа", "🧠 Твой умный собеседник")
    kb.row("🎥 Видео будущего", "🔉 Аудио с ИИ")
    kb.row("👤 Профиль", "❓ Помощь")
    kb.row("💰 Купить токены")

    return kb


# кнопка назад
def back():

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("⬅️ Назад")

    return kb


# старт
@bot.message_handler(commands=['start'])
def start(message):

    ref = None
    args = message.text.split()

    if len(args) > 1:
        try:
            ref = int(args[1])
        except:
            ref = None

    register_user(message.from_user, ref)

    send(
        message.chat.id,
        "✨ Добро пожаловать в Magic AI\n\nВыберите нужную функцию:",
        main_menu()
    )


@bot.message_handler(content_types=['photo'])
def photo_handler(message):

    user = message.from_user.id
    mode = user_modes.get(user)

    if mode != "image":
        return

    photo = message.photo[-1].file_id
    pending_edit[user] = photo

    bot.send_message(
        message.chat.id,
        "Теперь напишите, что нужно изменить на данной картинке."
    )


@bot.message_handler(func=lambda message: True)
def handler(message):

    text = message.text
    user = message.from_user.id
    mode = user_modes.get(user)

    if mode == "image":

        if user in pending_edit:

            photo_id = pending_edit[user]
            del pending_edit[user]

            msg = bot.send_message(
                message.chat.id,
                "🎨 Обрабатываю изображение..."
            )

            file_info = bot.get_file(photo_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

            result = edit_image(file_url, text)

            bot.send_photo(message.chat.id, result)

            return

        msg = bot.send_message(
            message.chat.id,
            "🎨 Генерирую изображение..."
        )

        result = generate_flux(text)

        bot.send_photo(message.chat.id, result)

        return


bot.infinity_polling()
