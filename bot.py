import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

chat_mode = {}


def main_menu():

    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )

    markup.row(
        InlineKeyboardButton("🧠 Твой умный собеседник", callback_data="chat")
    )

    markup.row(
        InlineKeyboardButton("🔉 Аудио с ИИ", callback_data="audio"),
        InlineKeyboardButton("🥷 Убийца фотошопа", callback_data="design")
    )

    markup.row(
        InlineKeyboardButton("🎥 Видео будущего", callback_data="video")
    )

    markup.row(
        InlineKeyboardButton("⁉️ Помощь", callback_data="help")
    )

    return markup


@bot.message_handler(commands=['start'])
def start(message):

    chat_mode[message.chat.id] = False

    bot.send_message(
        message.chat.id,
        "⚡ Добро пожаловать в AI-центр\n\nВыберите раздел:",
        reply_markup=main_menu()
    )


@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    chat_id = call.message.chat.id
    msg_id = call.message.message_id


    if call.data == "profile":

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton("💰 Баланс", callback_data="balance")
        )

        markup.row(
            InlineKeyboardButton("📊 Ваши запросы", callback_data="requests")
        )

        markup.row(
            InlineKeyboardButton("⭐ Подписка", callback_data="sub")
        )

        markup.row(
            InlineKeyboardButton("🤝 Реферальная ссылка", callback_data="ref")
        )

        markup.row(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )

        bot.edit_message_text(
            "👤 Ваш профиль",
            chat_id,
            msg_id,
            reply_markup=markup
        )


    elif call.data == "chat":

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton("🚀 Начнем", callback_data="start_chat")
        )

        markup.row(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )

        bot.edit_message_text(
            "🧠 Режим AI диалога",
            chat_id,
            msg_id,
            reply_markup=markup
        )


    elif call.data == "start_chat":

        chat_mode[chat_id] = True

        bot.send_message(
            chat_id,
            "Привет :)"
        )


    elif call.data == "audio":

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton("🎙️ ElevenLabs Voice", callback_data="voice")
        )

        markup.row(
            InlineKeyboardButton("🎵 ElevenLabs Music", callback_data="music")
        )

        markup.row(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )

        bot.edit_message_text(
            "🔉 Аудио с ИИ",
            chat_id,
            msg_id,
            reply_markup=markup
        )


    elif call.data == "design":

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton("🍌 Nano Banana PRO", callback_data="nano")
        )

        markup.row(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )

        bot.edit_message_text(
            "🥷 Генерация изображений",
            chat_id,
            msg_id,
            reply_markup=markup
        )


    elif call.data == "video":

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton("🎬 Kling", callback_data="kling")
        )

        markup.row(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )

        bot.edit_message_text(
            "🎥 Видео будущего",
            chat_id,
            msg_id,
            reply_markup=markup
        )


    elif call.data == "help":

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton("🚨 Служба поддержки", callback_data="support")
        )

        markup.row(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )

        bot.edit_message_text(
            "⁉️ Раздел помощи",
            chat_id,
            msg_id,
            reply_markup=markup
        )


    elif call.data == "menu":

        chat_mode[chat_id] = False

        bot.edit_message_text(
            "⚡ Главное меню",
            chat_id,
            msg_id,
            reply_markup=main_menu()
        )


@bot.message_handler(func=lambda message: True)
def chat(message):

    chat_id = message.chat.id

    if chat_mode.get(chat_id) != True:
        return

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": message.text}
            ]
        )

        answer = response.choices[0].message.content

        bot.send_message(chat_id, answer)

    except Exception as e:

        bot.send_message(chat_id, f"Ошибка: {e}")


bot.infinity_polling()
