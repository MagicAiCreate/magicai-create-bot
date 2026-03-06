import telebot
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я MagicAI Create. Напиши что-нибудь.")

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, "Ты написал: " + message.text)

bot.infinity_polling()
