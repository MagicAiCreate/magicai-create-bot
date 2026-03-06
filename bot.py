import os
import telebot
from telebot import types
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)


# ---------------- ГЛАВНОЕ МЕНЮ ----------------

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    btn1 = types.KeyboardButton("👤 Профиль")
    btn2 = types.KeyboardButton("🧠 Твой умный собеседник")
    btn3 = types.KeyboardButton("🔉 Аудио с ИИ")
    btn4 = types.KeyboardButton("🥷 Убийца фотошопа")
    btn5 = types.KeyboardButton("🎥 Видео будущего")
    btn6 = types.KeyboardButton("⁉️ Помощь")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)
    markup.add(btn6)

    return markup


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "Добро пожаловать в AI-центр ⚡",
                     reply_markup=main_menu())


# ---------------- ОБРАБОТКА КНОПОК ----------------

@bot.message_handler(func=lambda message: True)
def handle(message):

    text = message.text


# ---- ГЛАВНОЕ МЕНЮ ----

    if text == "🏠 Главное меню":
        bot.send_message(message.chat.id,
                         "Главное меню",
                         reply_markup=main_menu())
        return


# ---- ПРОФИЛЬ ----

    if text == "👤 Профиль":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        btn1 = types.KeyboardButton("💰 Баланс")
        btn2 = types.KeyboardButton("📊 Ваши запросы")
        btn3 = types.KeyboardButton("⭐ Подписка")
        btn4 = types.KeyboardButton("🤝 Реферальная ссылка")
        btn5 = types.KeyboardButton("🏠 Главное меню")

        markup.add(btn1)
        markup.add(btn2)
        markup.add(btn3)
        markup.add(btn4)
        markup.add(btn5)

        bot.send_message(message.chat.id,
                         "👤 Ваш профиль",
                         reply_markup=markup)
        return


# ---- УМНЫЙ СОБЕСЕДНИК ----

    if text == "🧠 Твой умный собеседник":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        btn1 = types.KeyboardButton("Начнем?")
        btn2 = types.KeyboardButton("🏠 Главное меню")

        markup.add(btn1)
        markup.add(btn2)

        bot.send_message(message.chat.id,
                         "Готов пообщаться с ИИ?",
                         reply_markup=markup)
        return


# ---- АУДИО ----

    if text == "🔉 Аудио с ИИ":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        btn1 = types.KeyboardButton("🎙️ ElevenLabs Voice")
        btn2 = types.KeyboardButton("🎵 ElevenLabs Music")
        btn3 = types.KeyboardButton("🏠 Главное меню")

        markup.add(btn1)
        markup.add(btn2)
        markup.add(btn3)

        bot.send_message(message.chat.id,
                         "Выберите функцию",
                         reply_markup=markup)
        return


# ---- ДИЗАЙН ----

    if text == "🥷 Убийца фотошопа":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        btn1 = types.KeyboardButton("🍌 Nano Banana PRO")
        btn2 = types.KeyboardButton("🏠 Главное меню")

        markup.add(btn1)
        markup.add(btn2)

        bot.send_message(message.chat.id,
                         "Генерация изображений",
                         reply_markup=markup)
        return


# ---- ВИДЕО ----

    if text == "🎥 Видео будущего":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        btn1 = types.KeyboardButton("🎬 Kling")
        btn2 = types.KeyboardButton("🏠 Главное меню")

        markup.add(btn1)
        markup.add(btn2)

        bot.send_message(message.chat.id,
                         "Генерация видео",
                         reply_markup=markup)
        return


# ---- ПОМОЩЬ ----

    if text == "⁉️ Помощь":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        btn1 = types.KeyboardButton("🚨 Служба поддержки")
        btn2 = types.KeyboardButton("🏠 Главное меню")

        markup.add(btn1)
        markup.add(btn2)

        bot.send_message(message.chat.id,
                         "Чем можем помочь?",
                         reply_markup=markup)
        return


# ---- CHATGPT ----

    if text == "Начнем?":
        bot.send_message(message.chat.id,
                         "Напишите ваш вопрос 🤖")
        return


# ---- ОТВЕТ CHATGPT ----

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": text}
            ]
        )

        answer = response.choices[0].message.content

        bot.send_message(message.chat.id, answer)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")


bot.infinity_polling()
