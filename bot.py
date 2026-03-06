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

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add("👤 Профиль")
    markup.add("🧠 Твой умный собеседник")
    markup.add("🔉 Аудио с ИИ")
    markup.add("🥷 Убийца фотошопа")
    markup.add("🎥 Видео будущего")
    markup.add("⁉️ Помощь")

    return markup


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


# ГЛАВНОЕ МЕНЮ

    if text == "🏠 Главное меню":

        chat_mode[chat_id] = False

        bot.send_message(
            chat_id,
            "Главное меню",
            reply_markup=main_menu()
        )
        return


# ПРОФИЛЬ

    if text == "👤 Профиль":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        markup.add("💰 Баланс")
        markup.add("📊 Ваши запросы")
        markup.add("⭐ Подписка")
        markup.add("🤝 Реферальная ссылка")
        markup.add("🏠 Главное меню")

        bot.send_message(chat_id, "👤 Ваш профиль", reply_markup=markup)
        return


# УМНЫЙ СОБЕСЕДНИК

    if text == "🧠 Твой умный собеседник":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        markup.add("🚀 Начнем")
        markup.add("🏠 Главное меню")

        bot.send_message(chat_id, "Готов пообщаться с ИИ?", reply_markup=markup)
        return


    if text == "🚀 Начнем":

        chat_mode[chat_id] = True

        bot.send_message(chat_id, "Привет :)")
        return


# АУДИО

    if text == "🔉 Аудио с ИИ":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        markup.add("🎙️ ElevenLabs Voice")
        markup.add("🎵 ElevenLabs Music")
        markup.add("🏠 Главное меню")

        bot.send_message(chat_id, "Раздел аудио", reply_markup=markup)
        return


# ДИЗАЙН

    if text == "🥷 Убийца фотошопа":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        markup.add("🍌 Nano Banana PRO")
        markup.add("🏠 Главное меню")

        bot.send_message(chat_id, "Генерация изображений", reply_markup=markup)
        return


# ВИДЕО

    if text == "🎥 Видео будущего":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        markup.add("🎬 Kling")
        markup.add("🏠 Главное меню")

        bot.send_message(chat_id, "Генерация видео", reply_markup=markup)
        return


# ПОМОЩЬ

    if text == "⁉️ Помощь":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        markup.add("🚨 Служба поддержки")
        markup.add("🏠 Главное меню")

        bot.send_message(chat_id, "Раздел помощи", reply_markup=markup)
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
