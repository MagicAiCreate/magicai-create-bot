import telebot
import sqlite3
import os
import time
import requests
import json
import html
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN)

user_modes = {}
last_messages = {}

pending_edit = {}
pending_size = {}
generation_lock = {}
last_generated = {}

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS purchases(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
stars INTEGER,
tokens INTEGER,
payload TEXT,
created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE users ADD COLUMN last_seen TEXT")
except:
    pass

cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
cursor.execute("UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE last_seen IS NULL")

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
        """
        INSERT INTO users (user_id, username, tokens, requests, referrer, created_at, last_seen)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
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


def update_activity(user_id):

    cursor.execute(
        "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id=?",
        (user_id,)
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


# генерация изображения
def generate_flux(prompt, aspect_ratio="9:16"):

    url = "https://api.replicate.com/v1/predictions"

    headers = {
        "Authorization": "Token " + REPLICATE_API_TOKEN,
        "Content-Type": "application/json"
    }

    data = {
        "version": "fdf4cb96614227f3021c42f35bc92d4fd2e3e1ae9f50ca4004ffa8da64bf8dca",
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
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
            if isinstance(output, list) and len(output) > 0:
                return output[0]
            return None

        if status in ["failed", "canceled"]:
            return None


def edit_image(image_url, prompt, aspect_ratio="match_input_image"):

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
            "aspect_ratio": aspect_ratio,
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
            if isinstance(output, list) and len(output) > 0:
                return output[0]
            return None

        if status in ["failed", "canceled"]:
            return None


def generation_status(chat_id, steps):

    msg = bot.send_message(chat_id, steps[0])

    for step in steps[1:]:
        time.sleep(0.9)
        try:
            bot.edit_message_text(
                step,
                chat_id,
                msg.message_id
            )
        except:
            pass

    return msg


def result_keyboard(user_id):

    kb = telebot.types.InlineKeyboardMarkup()

    kb.add(
        telebot.types.InlineKeyboardButton(
            "💎 Доработать изображение",
            callback_data=f"rework_{user_id}"
        )
    )

    return kb


def size_keyboard():

    kb = telebot.types.InlineKeyboardMarkup(row_width=3)

    kb.add(
        telebot.types.InlineKeyboardButton("1:1", callback_data="size_1:1"),
        telebot.types.InlineKeyboardButton("16:9", callback_data="size_16:9"),
        telebot.types.InlineKeyboardButton("9:16", callback_data="size_9:16")
    )

    return kb


def build_result_caption(prompt, image_url, spent, remaining):

    safe_prompt = html.escape(prompt)

    return (
        f'Вот <a href="{image_url}">прямая ссылка</a> на качественную версию.\n\n'
        f"Ваш запрос: {safe_prompt}\n\n"
        f"Качество: 4К\n"
        f"Модель: Убийца Photoshop\n\n"
        f"Списано: 💎 {spent}\n"
        f"Осталось: 💎 {remaining}"
    )


def admin_stats():

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at)=DATE('now')")
    new_today = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_seen)=DATE('now')")
    active_today = cursor.fetchone()[0] or 0

    left_today = max(total_users - active_today, 0)

    cursor.execute("SELECT COALESCE(SUM(stars),0) FROM purchases WHERE DATE(created_at)=DATE('now')")
    stars_today = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COALESCE(SUM(tokens),0) FROM purchases WHERE DATE(created_at)=DATE('now')")
    tokens_today = cursor.fetchone()[0] or 0

    return f"""
📊 Статистика бота

👥 Пользователей всего: {total_users}

🆕 Новых за сегодня: {new_today}

🚪 Ушло сегодня: {left_today}

⭐ Заработано сегодня: {stars_today}

💎 Куплено токенов сегодня: {tokens_today}
"""


def clean(chat_id):

    if chat_id in last_messages:

        try:
            bot.delete_message(chat_id, last_messages[chat_id])
        except:
            pass


def send(chat_id, text, keyboard=None):

    clean(chat_id)

    msg = bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard
    )

    last_messages[chat_id] = msg.message_id


def main_menu():

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("🥷 Убийца фотошопа", "🧠 Твой умный собеседник")
    kb.row("🎥 Видео будущего", "🔉 Аудио с ИИ")
    kb.row("👤 Профиль", "❓ Помощь")
    kb.row("💰 Купить токены")

    return kb


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
    update_activity(message.from_user.id)

    send(
        message.chat.id,
        "✨ Добро пожаловать в Magic AI\n\nВыберите нужную функцию:",
        main_menu()
    )


@bot.message_handler(commands=['leopold'])
def leopold_panel(message):

    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(
        message.chat.id,
        admin_stats()
    )


@bot.message_handler(commands=['leopold_addme'])
def leopold_addme(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        amount = int(message.text.split()[1])

        cursor.execute(
            "UPDATE users SET tokens = tokens + ? WHERE user_id=?",
            (amount, ADMIN_ID)
        )

        db.commit()

        bot.send_message(
            message.chat.id,
            f"💎 Начислено вам: {amount}"
        )

    except:

        bot.send_message(
            message.chat.id,
            "Пример: /leopold_addme 1000"
        )


@bot.message_handler(commands=['leopold_give'])
def leopold_give(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        parts = message.text.split()

        user_id = int(parts[1])
        amount = int(parts[2])

        cursor.execute(
            "SELECT user_id FROM users WHERE user_id=?",
            (user_id,)
        )
        exists = cursor.fetchone()

        if not exists:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
            return

        cursor.execute(
            "UPDATE users SET tokens = tokens + ? WHERE user_id=?",
            (amount, user_id)
        )

        db.commit()

        bot.send_message(
            message.chat.id,
            f"💎 Пользователю {user_id} начислено: {amount}"
        )

    except:

        bot.send_message(
            message.chat.id,
            "Пример: /leopold_give 123456789 500"
        )


@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_query(query):

    bot.answer_pre_checkout_query(query.id, ok=True)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    user = call.from_user.id

    if call.data == "buy_250":

        prices = [telebot.types.LabeledPrice("250 tokens", 349)]

        bot.send_invoice(
            call.message.chat.id,
            title="💎 250 токенов",
            description="Пакет стандарт",
            invoice_payload="buy_250",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="buytokens250"
        )

        bot.answer_callback_query(call.id)
        return

    if call.data == "buy_500":

        prices = [telebot.types.LabeledPrice("500 tokens", 649)]

        bot.send_invoice(
            call.message.chat.id,
            title="🔥 500 токенов",
            description="Популярный пакет",
            invoice_payload="buy_500",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="buytokens500"
        )

        bot.answer_callback_query(call.id)
        return

    if call.data == "buy_1000":

        prices = [telebot.types.LabeledPrice("1000 tokens", 1099)]

        bot.send_invoice(
            call.message.chat.id,
            title="👑 1000 токенов",
            description="Максимальный пакет",
            invoice_payload="buy_1000",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="buytokens1000"
        )

        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("rework_"):

        target_user = int(call.data.split("_")[1])

        if user != target_user:
            bot.answer_callback_query(
                call.id,
                "❌ Эта кнопка не для вас."
            )
            return

        if target_user not in last_generated:
            bot.answer_callback_query(
                call.id,
                "❌ Изображение не найдено."
            )
            return

        pending_edit[target_user] = {
            "type": "generated",
            "value": last_generated[target_user]
        }

        bot.answer_callback_query(call.id)

        bot.send_message(
            call.message.chat.id,
            "Напишите, что нужно доработать на изображении."
        )
        return

    if call.data.startswith("size_"):

        aspect_ratio = call.data.replace("size_", "")

        if user not in pending_size:
            bot.answer_callback_query(
                call.id,
                "❌ Запрос не найден."
            )
            return

        cursor.execute(
            "SELECT tokens FROM users WHERE user_id=?",
            (user,)
        )
        row = cursor.fetchone()

        if not row:
            bot.answer_callback_query(
                call.id,
                "❌ Профиль не найден."
            )
            return

        tokens = row[0]

        if tokens < 25:
            bot.answer_callback_query(
                call.id,
                "❌ Недостаточно токенов. Нужно 25."
            )
            return

        task = pending_size[user]
        del pending_size[user]

        bot.answer_callback_query(call.id)

        if task["type"] == "edit":

            status_msg = generation_status(
                call.message.chat.id,
                [
                    "✅ Фото получено",
                    "🧠 Анализирую изменения...",
                    "🎨 Применяю правки...",
                    "💎 Почти закончил..."
                ]
            )

            result = edit_image(
                task["image_url"],
                task["prompt"],
                aspect_ratio
            )

            if result:
                cursor.execute(
                    "UPDATE users SET tokens = tokens - 25, requests = requests + 1 WHERE user_id=?",
                    (user,)
                )
                db.commit()

                remaining = tokens - 25
                last_generated[user] = result

                try:
                    bot.delete_message(call.message.chat.id, status_msg.message_id)
                except:
                    pass

                caption = build_result_caption(task["prompt"], result, 25, remaining)

                bot.send_photo(
                    call.message.chat.id,
                    result,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=result_keyboard(user)
                )
            else:
                bot.edit_message_text(
                    "❌ Ошибка при обработке изображения.",
                    call.message.chat.id,
                    status_msg.message_id
                )

            return

        if generation_lock.get(user):
            bot.send_message(
                call.message.chat.id,
                "⏳ Подождите завершения прошлой генерации."
            )
            return

        generation_lock[user] = True

        status_msg = generation_status(
            call.message.chat.id,
            [
                "✅ Запрос принят",
                "🧠 Улучшаю запрос...",
                "🎨 Начинается генерация...",
                "💎 Почти закончил..."
            ]
        )

        better_prompt = improve_prompt(task["prompt"])
        result = generate_flux(better_prompt, aspect_ratio)

        if result:

            cursor.execute(
                "UPDATE users SET tokens = tokens - 25, requests = requests + 1 WHERE user_id=?",
                (user,)
            )

            db.commit()

            remaining = tokens - 25
            last_generated[user] = result

            try:
                bot.delete_message(call.message.chat.id, status_msg.message_id)
            except:
                pass

            caption = build_result_caption(task["prompt"], result, 25, remaining)

            bot.send_photo(
                call.message.chat.id,
                result,
                caption=caption,
                parse_mode="HTML",
                reply_markup=result_keyboard(user)
            )

        else:

            bot.edit_message_text(
                "❌ Ошибка генерации изображения.",
                call.message.chat.id,
                status_msg.message_id
            )

        generation_lock[user] = False
        return


@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):

    payload = message.successful_payment.invoice_payload
    user = message.from_user.id

    if payload == "buy_250":
        tokens_add = 250
        stars_paid = 349

    elif payload == "buy_500":
        tokens_add = 500
        stars_paid = 649

    elif payload == "buy_1000":
        tokens_add = 1000
        stars_paid = 1099

    else:
        return

    cursor.execute(
        "UPDATE users SET tokens = tokens + ? WHERE user_id=?",
        (tokens_add, user)
    )

    cursor.execute(
        """
        INSERT INTO purchases (user_id, stars, tokens, payload)
        VALUES (?, ?, ?, ?)
        """,
        (user, stars_paid, tokens_add, payload)
    )

    db.commit()

    bot.send_message(
        message.chat.id,
        f"✨ Оплата прошла успешно\n\nНачислено: 💎 {tokens_add}"
    )


@bot.message_handler(content_types=['photo'])
def photo_handler(message):

    user = message.from_user.id
    mode = user_modes.get(user)

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user,))
    exists = cursor.fetchone()

    if not exists:
        register_user(message.from_user)

    update_activity(user)

    if mode != "image":
        return

    photo = message.photo[-1].file_id

    pending_edit[user] = {
        "type": "telegram",
        "value": photo
    }

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

    update_activity(user)

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
                "💎 250 токенов — стандарт ⭐349",
                callback_data="buy_250"
            )
        )

        kb.add(
            telebot.types.InlineKeyboardButton(
                "🔥 500 токенов — популярный ⭐649",
                callback_data="buy_500"
            )
        )

        kb.add(
            telebot.types.InlineKeyboardButton(
                "👑 1000 токенов — максимум ⭐1099",
                callback_data="buy_1000"
            )
        )

        bot.send_message(
            message.chat.id,
            "💳 Выберите пакет токенов\n\n1 изображение = 25 💎",
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

💎 Баланс токенов: {tokens}

📊 Использовано запросов: {requests_count}

━━━━━━━━━━━━━━━

🔗 Ваша реферальная ссылка

https://t.me/AiMagicCreateBot?start={user}

💸 Приглашайте друзей и получайте
+15 💎 за каждого нового пользователя.
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

Тариф: 💎25 токенов""",
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
            "💎 Запрос получен..."
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
                "❌ Недостаточно токенов. Нужно 25 💎."
            )
            return

        if user in pending_edit:

            edit_source = pending_edit[user]
            del pending_edit[user]

            if isinstance(edit_source, dict) and edit_source["type"] == "telegram":

                file_info = bot.get_file(edit_source["value"])
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

            else:

                file_url = edit_source["value"]

            pending_size[user] = {
                "type": "edit",
                "prompt": text,
                "image_url": file_url
            }

            bot.send_message(
                message.chat.id,
                "Какой размер изображения вы хотите?",
                reply_markup=size_keyboard()
            )

            return

        pending_size[user] = {
            "type": "generate",
            "prompt": text
        }

        bot.send_message(
            message.chat.id,
            "Какой размер изображения вы хотите?",
            reply_markup=size_keyboard()
        )

        return


bot.infinity_polling()
