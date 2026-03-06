import telebot
import sqlite3
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

user_modes = {}

# база
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


# регистрация
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


# меню
def main_menu():

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("👤 Профиль")
    keyboard.row("🧠 Твой умный собеседник")
    keyboard.row("🔉 Аудио с ИИ")
    keyboard.row("🥷 Убийца фотошопа")
    keyboard.row("🎥 Видео будущего")
    keyboard.row("⁉️ Помощь")

    return keyboard


# профиль меню
def profile_menu():

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("💰 Баланс")
    keyboard.row("📊 Мои запросы")
    keyboard.row("👥 Рефералы")
    keyboard.row("🪙 Купить токены")
    keyboard.row("🏠 Главное меню")

    return keyboard


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

    bot.send_message(
        message.chat.id,
        "⚡ Добро пожаловать в Magic AI 🤖",
        reply_markup=main_menu()
    )


@bot.message_handler(func=lambda message: True)
def handler(message):

    text = message.text
    user_id = message.from_user.id


    if text == "🏠 Главное меню":

        user_modes[user_id] = None

        bot.send_message(
            message.chat.id,
            "🏠 Главное меню",
            reply_markup=main_menu()
        )
        return


    if text == "👤 Профиль":

        cursor.execute(
            "SELECT tokens, requests FROM users WHERE user_id=?",
            (user_id,)
        )

        data = cursor.fetchone()

        tokens = data[0]
        requests = data[1]

        profile_text = f"""
👤 Профиль

🆔 ID: {user_id}
🪙 Токены: {tokens}
📊 Запросов: {requests}

🔗 Ваша реферальная ссылка:
https://t.me/AiMagicCreateBot?start={user_id}
"""

        bot.send_message(
            message.chat.id,
            profile_text,
            reply_markup=profile_menu()
        )
        return


    if text == "🧠 Твой умный собеседник":

        user_modes[user_id] = "chat"

        bot.send_message(
            message.chat.id,
            """🤖 Привет!

Я твой умный собеседник 😊  
Можешь говорить со мной о чем угодно.

Задай любой вопрос.

Чтобы выйти нажми:
🏠 Главное меню"""
        )
        return


    if text == "🥷 Убийца фотошопа":

        user_modes[user_id] = "image"

        bot.send_message(
            message.chat.id,
            """🥷 Убийца фотошопа

Привет! 🎨

Напиши запрос для генерации картинки.

Или отправь изображение и напиши,
что изменить на нём.

Чтобы выйти нажми:
🏠 Главное меню"""
        )
        return


    if text == "🔉 Аудио с ИИ":

        bot.send_message(
            message.chat.id,
            "🎧 Раздел аудио пока в разработке",
            reply_markup=main_menu()
        )
        return


    if text == "🎥 Видео будущего":

        bot.send_message(
            message.chat.id,
            "🎬 Видео генерация скоро появится",
            reply_markup=main_menu()
        )
        return


    if text == "⁉️ Помощь":

        bot.send_message(
            message.chat.id,
            "🚨 Напишите в поддержку",
            reply_markup=main_menu()
        )
        return


bot.infinity_polling()
