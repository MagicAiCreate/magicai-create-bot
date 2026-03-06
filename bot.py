import os
import telebot
from telebot import types
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

chat_mode = {}


def main_menu():

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("👤 Профиль")
    keyboard.row("🧠 Твой умный собеседник")
    keyboard.row("🔉 Аудио с ИИ", "🥷 Убийца фотошопа")
    keyboard.row("🎥 Видео будущего")
    keyboard.row("⁉️ Помощь")

    return keyboard


@bot.message_handler(commands=['start'])
def start(message):

    chat_mode[message.chat.id] = False

    bot.send_message(
        message.chat.id,
        "⚡ Добро пожаловать в AI-центр",
        reply_markup=main_menu()
    )


@bot.message_handler(func=lambda message: True)
def handle(message):

    chat_id = message.chat.id
    text = message.text


# удаляем сообщение пользователя если он не в AI-чате
    if chat_mode.get(chat_id) != True:

        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass


# ПРОФИЛЬ
    if text == "👤 Профиль":

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("💰 Баланс")
        keyboard.row("📊 Ваши запросы")
        keyboard.row("⭐ Подписка")
        keyboard.row("🤝 Реферальная ссылка")
        keyboard.row("🏠 Главное меню")

        bot.send_message(chat_id, "👤 Ваш профиль", reply_markup=keyboard)
        return


# AI ЧАТ
    if text == "🧠 Твой умный собеседник":

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🚀 Начнем")
        keyboard.row("🏠 Главное меню")

        bot.send_message(chat_id, "Готов пообщаться с ИИ?", reply_markup=keyboard)
        return


    if text == "🚀 Начнем":

        chat_mode[chat_id] = True

        bot.send_message(chat_id, "Привет :)")
        return


# АУДИО
    if text == "🔉 Аудио с ИИ":

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🎙️ ElevenLabs Voice")
        keyboard.row("🎵 ElevenLabs Music")
        keyboard.row("🏠 Главное меню")

        bot.send_message(chat_id, "Раздел аудио", reply_markup=keyboard)
        return


# ДИЗАЙН
    if text == "🥷 Убийца фотошопа":

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🍌 Nano Banana PRO")
        keyboard.row("🏠 Главное меню")

        bot.send_message(chat_id, "Генерация изображений", reply_markup=keyboard)
        return


# ВИДЕО
    if text == "🎥 Видео будущего":

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🎬 Kling")
        keyboard.row("🏠 Главное меню")

        bot.send_message(chat_id, "Генерация видео", reply_markup=keyboard)
        return


# ПОМОЩЬ
    if text == "⁉️ Помощь":

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        keyboard.row("🚨 Служба поддержки")
        keyboard.row("🏠 Главное меню")

        bot.send_message(chat_id, "Чем можем помочь?", reply_markup=keyboard)
        return


# ГЛАВНОЕ МЕНЮ
    if text == "🏠 Главное меню":

        chat_mode[chat_id] = False

        bot.send_message(
            chat_id,
            "Главное меню",
            reply_markup=main_menu()
        )
        return


# CHATGPT
    if chat_mode.get(chat_id) == True:

        try:

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": text}
                ]
            )

            answer = response.choices[0].message.content

            bot.send_message(chat_id, answer)

        except Exception as e:

            bot.send_message(chat_id, f"Ошибка: {e}")


bot.infinity_polling()
