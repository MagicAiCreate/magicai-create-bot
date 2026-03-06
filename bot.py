import telebot
import sqlite3
import os
import time
import requests
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

user_modes = {}
last_messages = {}

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


# Flux генерация
def generate_flux(prompt):

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "version": "black-forest-labs/flux-schnell",
        "input": {
            "prompt": prompt,
            "aspect_ratio": "9:16"
        }
    }

    r = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers=headers,
        json=data
    )

    prediction = r.json()
    prediction_id = prediction["id"]

    while True:

        r = requests.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers=headers
        )

        result = r.json()

        if result["status"] == "succeeded":
            return result["output"][0]

        if result["status"] == "failed":
            return None

        time.sleep(1)


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


@bot.message_handler(func=lambda message: True)
def handler(message):

    text = message.text
    user = message.from_user.id
    mode = user_modes.get(user)

    if mode not in ["chat", "image", "audio", "video"]:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass


    if text == "🥷 Убийца фотошопа":

        user_modes[user] = "image"

        send(
            message.chat.id,
            """🥷 Убийца фотошопа

Создавайте изображения по текстовому описанию.

Например:
• Машина, деньги на капоте, вечер, дождь, Москва-Сити, формат 9:16.

Или загрузите фото и укажите, что изменить:
• удалить объект
• заменить фон
• улучшить качество
• изменить стиль
• добавить новый элемент

Обработка занимает несколько секунд.

Тариф: ⚡️25 токенов""",
            back()
        )
        return


    if mode == "image":

        cursor.execute(
            "SELECT tokens FROM users WHERE user_id=?",
            (user,)
        )

        tokens = cursor.fetchone()[0]

        if tokens < 25:

            bot.send_message(
                message.chat.id,
                "❌ Недостаточно токенов. Нужно 25."
            )
            return


        msg = bot.send_message(
            message.chat.id,
            "🎨 Генерирую изображение..."
        )

        image_url = generate_flux(text)

        if image_url:

            cursor.execute(
                "UPDATE users SET tokens = tokens - 25 WHERE user_id=?",
                (user,)
            )

            db.commit()

            bot.delete_message(message.chat.id, msg.message_id)

            bot.send_photo(
                message.chat.id,
                image_url,
                caption="✨ Готово!"
            )

        else:

            bot.edit_message_text(
                "❌ Ошибка генерации",
                message.chat.id,
                msg.message_id
            )

        return


bot.infinity_polling()
