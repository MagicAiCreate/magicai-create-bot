import os
import telebot
from telebot import types
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    btn1 = types.KeyboardButton("ChatGPT")
    btn2 = types.KeyboardButton("NanoBanana")
    btn3 = types.KeyboardButton("Kling")

    markup.add(btn1, btn2)
    markup.add(btn3)

    bot.send_message(message.chat.id, "Выберите инструмент:", reply_markup=markup)


@bot.message_handler(func=lambda message: True)
def chat(message):

    if message.text == "NanoBanana":
        bot.send_message(message.chat.id, "NanoBanana скоро будет подключена.")
        return

    if message.text == "Kling":
        bot.send_message(message.chat.id, "Kling скоро будет подключен.")
        return

    if message.text == "ChatGPT":
        bot.send_message(message.chat.id, "Напиши вопрос.")
        return

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": message.text}
            ]
        )

        answer = response.choices[0].message.content
        bot.send_message(message.chat.id, answer)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")


bot.infinity_polling()
