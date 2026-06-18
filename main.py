import random
import telebot
from telebot import types
from flask import Flask
from threading import Thread

TOKEN = '8959290931:AAFRYtCsCzMGJ_fK7okqtjLFiMasXuOxVGs'
bot = telebot.TeleBot(TOKEN)

CARDS = [
    {"name": "🃏 Обычный Джокер", "rarity": "Common (Обычная)", "chance": 50},
    {"name": "⚔️ Рыцарь Мечей", "rarity": "Rare (Редкая)", "chance": 30},
    {"name": "🧙‍♂️ Верховный Маг", "rarity": "Epic (Эпическая)", "chance": 15},
    {"name": "🐉 Золотой Дракон", "rarity": "Legendary (Легендарная)", "chance": 4},
    {"name": "👑 Создатель Миров", "rarity": "Mythic (Мифическая)", "chance": 1}
]

def get_random_card():
    weights = [card["chance"] for card in CARDS]
    return random.choices(CARDS, weights=weights, k=1)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("🎴 Тянуть карточку")
    markup.add(btn)
    bot.send_message(message.chat.id, "Привет! Нажми на кнопку ниже или введи команду /get", reply_markup=markup)

@bot.message_handler(commands=['get'])
@bot.message_handler(func=lambda message: message.text == "🎴 Тянуть карточку")
def draw_card(message):
    card = get_random_card()[0]
    text = f"✨ **Вы вытянули карточку!** ✨\n\n🏷️ **Название:** {card['name']}\n💎 **Ценность:** {card['rarity']}\n📊 **Шанс:** {card['chance']}%"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

app = Flask('')
@app.route('/')
def home():
    return "Бот работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

if __name__ == '__main__':
    keep_alive()
    bot.remove_webhook()
    print("Бот успешно запущен!")
    bot.infinity_polling()
