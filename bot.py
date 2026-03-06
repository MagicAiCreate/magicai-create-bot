import os
import telebot
import sqlite3
import time
from telebot import types
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

ADMIN_ID = 816154985
BOT_USERNAME = "AiMagicCreateBot"

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

chat_mode = {}
conversation_history = {}
cooldowns = {}

db = sqlite3.connect("users.db", check_same_thread=False)
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


def register_user(user, ref=None):

    cursor.execute("SELECT user_id, referrer FROM users WHERE user_id=?", (user.id,))
    exists = cursor.fetchone()

    # если пользователь уже есть в базе — ничего не делаем
    if exists:
        return

    username = user.username if user.username else "none"
    referrer = None

    # проверяем реферала
    if ref and ref != user.id:

        cursor.execute("SELECT user_id FROM users WHERE user_id=?", (ref,))
        ref_exists = cursor.fetchone()

        if ref_exists:
            referrer = ref

            # начисляем 15 токенов пригласившему
            cursor.execute(
                "UPDATE users SET tokens = tokens + 15 WHERE user_id=?",
                (ref,)
            )

    # регистрируем нового пользователя
    cursor.execute(
        "INSERT INTO users (user_id, username, tokens, requests, referrer) VALUES (?,?,?,?,?)",
        (user.id, username, 50, 0, referrer)
    )

    db.commit()

def get_user(user_id):

    cursor.execute("SELECT tokens,requests FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()


def add_request(user_id):

    cursor.execute(
    "UPDATE users SET requests=requests+1 WHERE user_id=?",
    (user_id,)
    )
    db.commit()


def remove_tokens(user_id, amount):

    cursor.execute(
    "UPDATE users SET tokens=tokens-? WHERE user_id=?",
    (amount,user_id)
    )
    db.commit()


def main_menu():

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("👤 Профиль")
    kb.row("🧠 Твой умный собеседник")
    kb.row("🔉 Аудио с ИИ","🥷 Убийца фотошопа")
    kb.row("🎥 Видео будущего")
    kb.row("💰 Купить токены")
    kb.row("⁉️ Помощь")

    return kb


@bot.message_handler(commands=["start"])
def start(message):

    ref = None

    if len(message.text.split()) > 1:
        ref = int(message.text.split()[1])

    register_user(message.from_user, ref)

    chat_mode[message.chat.id] = False

    conversation_history[message.chat.id] = [
    {"role":"system","content":"Ты дружелюбный AI ассистент."}
    ]

    bot.send_message(
    message.chat.id,
    "⚡ Добро пожаловать в Magic AI",
    reply_markup=main_menu()
    )


@bot.message_handler(func=lambda m:True)
def handler(message):

    chat_id = message.chat.id
    text = message.text

    if chat_mode.get(chat_id) != True:
        try:
            bot.delete_message(chat_id,message.message_id)
        except:
            pass

    elif text == "👤 Профиль":

    cursor.execute(
        "SELECT tokens, requests FROM users WHERE user_id=?",
        (message.from_user.id,)
    )

    data = cursor.fetchone()

    tokens = data[0]
    requests = data[1]

    profile_text = f"""
👤 Профиль

ID: {message.from_user.id}
Токены: {tokens}
Запросов: {requests}

Ваша реферальная ссылка:
https://t.me/AiMagicCreateBot?start={message.from_user.id}
"""

    profile_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    profile_keyboard.row("💰 Баланс")
    profile_keyboard.row("📊 Мои запросы")
    profile_keyboard.row("👥 Рефералы")
    profile_keyboard.row("🪙 Купить токены")
    profile_keyboard.row("🏠 Главное меню")

    bot.send_message(
        message.chat.id,
        profile_text,
        reply_markup=profile_keyboard
    )

        data = get_user(chat_id)

        tokens = data[0]
        requests = data[1]

        ref_link = f"https://t.me/{BOT_USERNAME}?start={chat_id}"

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🏠 Главное меню")

        bot.send_message(
        chat_id,
        f"👤 Профиль\n\n"
        f"ID: {chat_id}\n"
        f"Токены: {tokens}\n"
        f"Запросов: {requests}\n\n"
        f"Ваша реферальная ссылка:\n{ref_link}",
        reply_markup=kb
        )

        return


    if text == "🧠 Твой умный собеседник":

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🚀 Начать")
        kb.row("🏠 Главное меню")

        bot.send_message(chat_id,"Начать диалог?",reply_markup=kb)
        return


    if text == "🚀 Начать":

        chat_mode[chat_id] = True
        bot.send_message(chat_id,"Привет :)")
        return


    if text == "🔉 Аудио с ИИ":

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🎙 ElevenLabs Voice")
        kb.row("🎵 ElevenLabs Music")
        kb.row("🏠 Главное меню")

        bot.send_message(chat_id,"Раздел аудио",reply_markup=kb)
        return


    if text == "🥷 Убийца фотошопа":

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🍌 Nano Banana")
        kb.row("🏠 Главное меню")

        bot.send_message(chat_id,"Генерация изображений",reply_markup=kb)
        return


    if text == "🎥 Видео будущего":

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🎬 Kling")
        kb.row("🏠 Главное меню")

        bot.send_message(chat_id,"Генерация видео",reply_markup=kb)
        return


    if text == "💰 Купить токены":

        bot.send_message(
        chat_id,
        "Раздел оплаты скоро появится"
        )
        return


    if text == "⁉️ Помощь":

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🚨 Служба поддержки")
        kb.row("🏠 Главное меню")

        bot.send_message(chat_id,"Напишите поддержку",reply_markup=kb)
        return


    if text == "🏠 Главное меню":

        chat_mode[chat_id] = False

        bot.send_message(
        chat_id,
        "Главное меню",
        reply_markup=main_menu()
        )
        return


    if chat_mode.get(chat_id) == True:

        if chat_id in cooldowns:
            if time.time() - cooldowns[chat_id] < 2:
                return

        cooldowns[chat_id] = time.time()

        user = get_user(chat_id)

        if user[0] <= 0:
            bot.send_message(chat_id,"Недостаточно токенов")
            return

        try:

            remove_tokens(chat_id,1)
            add_request(chat_id)

            conversation_history[chat_id].append(
            {"role":"user","content":text}
            )

            response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history[chat_id]
            )

            answer = response.choices[0].message.content

            conversation_history[chat_id].append(
            {"role":"assistant","content":answer}
            )

            conversation_history[chat_id] = conversation_history[chat_id][-20:]

            bot.send_message(chat_id,answer)

        except Exception as e:

            bot.send_message(chat_id,f"Ошибка: {e}")


bot.infinity_polling()
