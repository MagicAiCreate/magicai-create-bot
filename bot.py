import telebot
import sqlite3
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

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
        "⚡ Добро пожаловать в Magic AI",
        main_menu()
    )


@bot.message_handler(func=lambda message: True)
def handler(message):

    text = message.text
    user = message.from_user.id


    if text == "⬅️ Назад":

        user_modes[user] = None

        send(
            message.chat.id,
            "🏠 Главное меню",
            main_menu()
        )
        return


    if text == "👤 Профиль":

        cursor.execute(
            "SELECT tokens, requests FROM users WHERE user_id=?",
            (user,)
        )

        data = cursor.fetchone()

        tokens = data[0]
        requests = data[1]

        text_profile = f"""
👤 Профиль

🆔 ID: {user}
🪙 Токены: {tokens}
📊 Запросов: {requests}

🔗 Ваша реферальная ссылка
https://t.me/AiMagicCreateBot?start={user}

💰 Хочешь заработать?

Отправь эту ссылку друзьям.
За каждого приглашённого друга
ты получишь 15 токенов.
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

🎨 Привет!

Напиши описание изображения
или отправь фото и напиши
что нужно изменить.

⏳ ИИ готов к генерации...""",
            back()
        )
        return


    if text == "🧠 Твой умный собеседник":

        user_modes[user] = "chat"

        send(
            message.chat.id,
            """🤖 Привет!

Я твой умный собеседник.

Можешь задать любой вопрос,
попросить совет или просто
поговорить со мной.

🧠 Я готов к диалогу.""",
            back()
        )
        return


    if text == "🎥 Видео будущего":

        send(
            message.chat.id,
            """🎥 Видео будущего

🚀 Скоро здесь появится
генерация AI видео.

Следи за обновлениями!""",
            back()
        )
        return


    if text == "🔉 Аудио с ИИ":

        send(
            message.chat.id,
            """🔉 Аудио с ИИ

🎧 Генерация аудио скоро
появится в этом разделе.""",
            back()
        )
        return


    if text == "❓ Помощь":

        send(
            message.chat.id,
            """❓ Помощь

Если возникли вопросы —
обратитесь в поддержку.""",
            back()
        )
        return


    mode = user_modes.get(user)


    if mode == "chat":

        send(
            message.chat.id,
            "🧠 ИИ думает..."
        )

        bot.send_message(
            message.chat.id,
            "🤖 Пока ИИ не подключён. Скоро добавим."
        )

        return


    if mode == "image":

        send(
            message.chat.id,
            "🎨 Генерирую изображение..."
        )

        bot.send_message(
            message.chat.id,
            "🖼 Генерация скоро будет подключена."
        )

        return


bot.infinity_polling()
