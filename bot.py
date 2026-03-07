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

    row = cursor.fetchone()
    if not row:
        return "❌ Пользователь не найден."

    tokens = row[0]

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

    r = requests.post(url, headers=headers, json=data, timeout=90)
    result = r.json()

    if "choices" not in result:
        return "❌ Ошибка ответа от AI."

    answer = result["choices"][0]["message"]["content"]

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


# улучшение промпта для генерации
def improve_prompt(prompt):

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }

    system = """Ты профессиональный AI prompt engineer.
Превращай короткие пользовательские запросы в детализированные промпты
для генерации фотореалистичных изображений.

Добавляй:
детали сцены
освещение
камеру
реализм
киношный стиль

Не объясняй ничего.
Выводи только улучшенный промпт."""

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    r = requests.post(url, headers=headers, json=data, timeout=60)
    result = r.json()

    if "choices" not in result:
        return prompt

    return result["choices"][0]["message"]["content"]


# генерация изображения через Replicate nano-banana-pro
def generate_flux(prompt):

    url = "https://api.replicate.com/v1/predictions"

    headers = {
        "Authorization": "Token " + REPLICATE_API_TOKEN,
        "Content-Type": "application/json"
    }

    data = {
        "version": "fdf4cb96614227f3021c42f35bc92d4fd2e3e1ae9f50ca4004ffa8da64bf8dca",
        "input": {
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "resolution": "2K",
            "output_format": "jpg",
            "safety_filter_level": "block_only_high",
            "allow_fallback_model": True
        }
    }

    r = requests.post(url, headers=headers, json=data, timeout=120)
    prediction = r.json()

    if "id" not in prediction:
        return None

    prediction_id = prediction["id"]

    while True:

        time.sleep(2)

        r = requests.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers=headers,
            timeout=120
        )

        result = r.json()
        status = result.get("status")

        if status == "succeeded":
            output = result.get("output")
            if isinstance(output, str):
                return output
            return None

        if status in ["failed", "canceled"]:
            return None


# редактирование изображения через Replicate nano-banana-pro
def edit_image(image_url, prompt):

    url = "https://api.replicate.com/v1/predictions"

    headers = {
        "Authorization": "Token " + REPLICATE_API_TOKEN,
        "Content-Type": "application/json"
    }

    data = {
        "version": "fdf4cb96614227f3021c42f35bc92d4fd2e3e1ae9f50ca4004ffa8da64bf8dca",
        "input": {
            "prompt": prompt,
            "image_input": [image_url],
            "aspect_ratio": "match_input_image",
            "resolution": "2K",
            "output_format": "jpg",
            "safety_filter_level": "block_only_high",
            "allow_fallback_model": True
        }
    }

    r = requests.post(url, headers=headers, json=data, timeout=120)
    prediction = r.json()

    if "id" not in prediction:
        return None

    prediction_id = prediction["id"]

    while True:

        time.sleep(2)

        r = requests.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers=headers,
            timeout=120
        )

        result = r.json()
        status = result.get("status")

        if status == "succeeded":
            output = result.get("output")
            if isinstance(output, str):
                return output
            return None

        if status in ["failed", "canceled"]:
            return None


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


@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    user = call.from_user.id

    if call.data == "buy_50":

        bot.answer_callback_query(call.id)

        cursor.execute(
            "UPDATE users SET tokens = tokens + 50 WHERE user_id=?",
            (user,)
        )

        db.commit()

        bot.send_message(
            call.message.chat.id,
            "⭐ Вам начислено 50 токенов."
        )

    if call.data == "buy_150":

        bot.answer_callback_query(call.id)

        cursor.execute(
            "UPDATE users SET tokens = tokens + 150 WHERE user_id=?",
            (user,)
        )

        db.commit()

        bot.send_message(
            call.message.chat.id,
            "⭐ Вам начислено 150 токенов."
        )


@bot.message_handler(content_types=['photo'])
def photo_handler(message):

    user = message.from_user.id
    mode = user_modes.get(user)

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user,))
    exists = cursor.fetchone()

    if not exists:
        register_user(message.from_user)

    if mode != "image":
        return

    photo = message.photo[-1].file_id
    pending_edit[user] = photo

    bot.send_message(
        message.chat.id,
        "Теперь напишите, что нужно изменить на данной картинке."
    )


@bot.message_handler(content_types=['text'])
def handler(message):

    text = message.text
    user = message.from_user.id
    mode = user_modes.get(user)

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user,))
    exists = cursor.fetchone()

    if not exists:
        register_user(message.from_user)

    # эффект Таноса
    if mode is None:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass


    if text == "⬅️ Назад":

        user_modes[user] = None

        send(
            message.chat.id,
            "🏠 Главное меню",
            main_menu()
        )
        return


    if text == "💰 Купить токены":

        kb = telebot.types.InlineKeyboardMarkup()

        kb.add(
            telebot.types.InlineKeyboardButton(
                "50 токенов ⭐50",
                callback_data="buy_50"
            )
        )

        kb.add(
            telebot.types.InlineKeyboardButton(
                "150 токенов ⭐120",
                callback_data="buy_150"
            )
        )

        bot.send_message(
            message.chat.id,
            "💳 Выберите пакет токенов:",
            reply_markup=kb
        )
        return


    if text == "👤 Профиль":

        cursor.execute(
            "SELECT tokens, requests FROM users WHERE user_id=?",
            (user,)
        )

        row = cursor.fetchone()
        if not row:
            bot.send_message(message.chat.id, "❌ Профиль не найден.")
            return

        tokens, requests_count = row

        text_profile = f"""
👤 Ваш профиль

━━━━━━━━━━━━━━━

🆔 ID: {user}

🪙 Баланс токенов: {tokens}

📊 Использовано запросов: {requests_count}

━━━━━━━━━━━━━━━

🔗 Ваша реферальная ссылка

https://t.me/AiMagicCreateBot?start={user}

💸 Приглашайте друзей и получайте
+15 токенов за каждого нового пользователя.
"""

        send(
            message.chat.id,
            text_profile,
            back()
        )
        return


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


    if text == "🧠 Твой умный собеседник":

        user_modes[user] = "chat"

        send(
            message.chat.id,
            """🧠 Твой умный собеседник!

Привет, хочешь просто поговорить или что-то узнать? Пиши, отвечу)""",
            back()
        )
        return


    if text == "🎥 Видео будущего":

        user_modes[user] = "video"

        send(
            message.chat.id,
            """🎥 Генерация видео

Скоро здесь появится
создание AI видео.""",
            back()
        )
        return


    if text == "🔉 Аудио с ИИ":

        user_modes[user] = "audio"

        send(
            message.chat.id,
            """🔉 Генерация аудио

Функция скоро появится.""",
            back()
        )
        return


    if text == "❓ Помощь":

        send(
            message.chat.id,
            """❓ Помощь

Если возникли вопросы —
напишите в поддержку.""",
            back()
        )
        return


    if mode == "chat":

        msg = bot.send_message(
            message.chat.id,
            "⚡ Запрос получен..."
        )

        time.sleep(0.7)

        bot.edit_message_text(
            "🧠 Анализирую данные...",
            message.chat.id,
            msg.message_id
        )

        time.sleep(0.7)

        bot.edit_message_text(
            "🤖 Генерирую ответ...",
            message.chat.id,
            msg.message_id
        )

        answer = ask_gpt(user, text)

        bot.edit_message_text(
            f"✨ {answer}",
            message.chat.id,
            msg.message_id
        )

        return


    if mode == "image":

        cursor.execute(
            "SELECT tokens FROM users WHERE user_id=?",
            (user,)
        )
        row = cursor.fetchone()

        if not row:
            bot.send_message(message.chat.id, "❌ Профиль не найден.")
            return

        tokens = row[0]

        if tokens < 25:
            bot.send_message(
                message.chat.id,
                "❌ Недостаточно токенов. Нужно 25."
            )
            return

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

            if result:
                cursor.execute(
                    "UPDATE users SET tokens = tokens - 25, requests = requests + 1 WHERE user_id=?",
                    (user,)
                )
                db.commit()

                bot.delete_message(message.chat.id, msg.message_id)
                bot.send_photo(message.chat.id, result)
            else:
                bot.edit_message_text(
                    "❌ Ошибка при обработке изображения.",
                    message.chat.id,
                    msg.message_id
                )

            return

        if generation_lock.get(user):
            bot.send_message(
                message.chat.id,
                "⏳ Подождите завершения прошлой генерации."
            )
            return

        generation_lock[user] = True

        msg = bot.send_message(
            message.chat.id,
            "🎨 Генерирую изображение..."
        )

        better_prompt = improve_prompt(text)
        result = generate_flux(better_prompt)

        if result:
            cursor.execute(
                "UPDATE users SET tokens = tokens - 25, requests = requests + 1 WHERE user_id=?",
                    (user,)
            )
            db.commit()

            bot.delete_message(message.chat.id, msg.message_id)
            bot.send_photo(message.chat.id, result)
        else:
            bot.edit_message_text(
                "❌ Ошибка генерации изображения.",
                message.chat.id,
                msg.message_id
            )

        generation_lock[user] = False

        return


bot.infinity_polling()
