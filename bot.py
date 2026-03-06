import telebot
import sqlite3
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

# режимы пользователей
user_modes = {}

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


# главное меню
def main_menu():

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("👤 Профиль")
    keyboard.row("🧠 Твой умный собеседник")
    keyboard.row("🔉 Аудио с ИИ")
    keyboard.row("🥷 Убийца фотошопа")
    keyboard.row("🎥 Видео будущего")
    keyboard.row("⁉️ Помощь")

    return keyboard


# профиль клавиатура
def profile_menu():

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("💰 Баланс")
    keyboard.row("📊 Мои запросы")
    keyboard.row("👥 Рефералы")
    keyboard.row("🪙 Купить токены")
    keyboard.row("🏠 Главное меню")

    return keyboard


# старт
@bot.message_handler(commands=["start"])
def start(message):

    ref = None

    args = message.text.split()

    if len(args) > 1:
        try:
            ref = int(args[1])
        except:
            ref = None

    register_user(message.from_user, ref)

    bot.send_message(
        message.chat.id,
        "⚡ Добро пожаловать в Magic AI 🤖",
        reply_markup=main_menu()
    )


# обработка сообщений
@bot.message_handler(func=lambda message: True)
def handler(message):

    text = message.text

    # профиль
    if text == "👤 Профиль":

        cursor.execute(
            "SELECT tokens, requests FROM users WHERE user_id=?",
            (message.from_user.id,)
        )

        data = cursor.fetchone()

        tokens = data[0]
        requests = data[1]

        profile_text = f"""
👤 Профиль

🆔 ID: {message.from_user.id}
🪙 Токены: {tokens}
📊 Запросов: {requests}

🔗 Ваша реферальная ссылка:
https://t.me/AiMagicCreateBot?start={message.from_user.id}
"""

        bot.send_message(
            message.chat.id,
            profile_text,
            reply_markup=profile_menu()
        )


    # главное меню
    elif text == "🏠 Главное меню":

        user_modes[message.from_user.id] = None

        bot.send_message(
            message.chat.id,
            "🏠 Главное меню",
            reply_markup=main_menu()
        )


    # AI чат
    elif text == "🧠 Твой умный собеседник":

        user_modes[message.from_user.id] = "chat_ai"

        bot.send_message(
            message.chat.id,
            """🤖 Привет!

Я теперь твой умный собеседник 😊

Ты можешь поговорить со мной на любые темы.

❓Задай любой вопрос  
💡 Попроси совет  
🧠 Обсуди любую идею

Я постараюсь помочь!

Чтобы выйти нажми:
🏠 Главное меню"""
        )


    # аудио
    elif text == "🔉 Аудио с ИИ":

        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🎙️ ElevenLabs Voice")
        keyboard.row("🎵 ElevenLabs Music")
        keyboard.row("🏠 Главное меню")

        bot.send_message(
            message.chat.id,
            "🎧 Раздел аудио ИИ",
            reply_markup=keyboard
        )


    # убийца фотошопа
    elif text == "🥷 Убийца фотошопа":

        user_modes[message.from_user.id] = "image_ai"

        bot.send_message(
            message.chat.id,
            """🥷 Убийца фотошопа

Привет! 🎨

Я могу создать для тебя любую картинку.

✏️ Напиши текст —
какую картинку ты хочешь сгенерировать.

🖼 Или отправь изображение
и напиши что на нём изменить.

Например:
"сделай ночь"
"добавь огонь"
"измени фон"

Чтобы выйти нажми:
🏠 Главное меню"""
        )


    # видео
    elif text == "🎥 Видео будущего":

        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🎬 Kling")
        keyboard.row("🏠 Главное меню")

        bot.send_message(
            message.chat.id,
            "🎬 Раздел видео ИИ",
            reply_markup=keyboard
        )


    # помощь
    elif text == "⁉️ Помощь":

        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🚨 Служба поддержки")
        keyboard.row("🏠 Главное меню")

        bot.send_message(
            message.chat.id,
            "❓ Если возникли вопросы — напишите в поддержку",
            reply_markup=keyboard
        )


bot.infinity_polling()
