import os
import random
import logging
from datetime import datetime, timedelta
from threading import Thread
import telebot
from telebot import types
from flask import Flask

TOKEN = '8959290931:AAFRYtCsCzMGJ_fK7okqtjLFiMasXuOxVGs'
bot = telebot.TeleBot(TOKEN)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

user_cooldowns = {}
user_balances = {}

user_inventories = {}

user_compounds = {}

COOLDOWN_HOURS = 3
COMPOUND_PRICE = 500

RARITY_DATA = {
"Common (Обычная)": {"chance": 55.0, "sell_price": 50},
"Rare (Редкая)": {"chance": 28.0, "sell_price": 150},
"Epic (Эпическая)": {"chance": 12.0, "sell_price": 400},
"Legendary (Легендарная)": {"chance": 4.2, "sell_price": 1000},
"Mythic (Мифическая)": {"chance": 0.8, "sell_price": 5000}
}

CARDS = [
{"name": "🇫🇷 Французик (Frenchie)", "rarity": "Common (Обычная)"},
{"name": "🥛 ММ (Mother's Milk)", "rarity": "Common (Обычная)"},
{"name": "👔 Тодд (Todd)", "rarity": "Common (Обычная)"},
{"name": "🧬 Хью Кэмпбелл-старший", "rarity": "Common (Обычная)"},

{"name": "🩸 Кимико (The Female)", "rarity": "Rare (Редкая)"},
{"name": "🏹 Хьюи Кэмпбелл (Hughie)", "rarity": "Rare (Редкая)"},
{"name": "🪵 Слепцов (Blindspot)", "rarity": "Rare (Редкая)"},
{"name": "🔫 Эшли Барретт (Ashley)", "rarity": "Rare (Редкая)"},

{"name": "🪓 Билли Бутчер (Billy Butcher)", "rarity": "Epic (Эпическая)"},
{"name": "🧠 Подводный (The Deep)", "rarity": "Epic (Эпическая)"},
{"name": "🦇 Ноар / Черный Нуар (Black Noir)", "rarity": "Epic (Эпическая)"},
{"name": "🗣️ Сестра Сэйдж (Sister Sage)", "rarity": "Epic (Эпическая)"},

{"name": "⚡ Поезд-А (A-Train)", "rarity": "Legendary (Легендарная)"},
{"name": "👑 Солдатик (Soldier Boy)", "rarity": "Legendary (Легендарная)"},
{"name": "✨ Звёздочка (Starlight)", "rarity": "Legendary (Легендарная)"},
{"name": "⚔️ Королева Мэйв (Queen Maeve)", "rarity": "Legendary (Легендарная)"},

{"name": "🥛 Хоумлендер (Homelander)", "rarity": "Mythic (Мифическая)"},
{"name": "🩸 Райан Бутчер (Ryan)", "rarity": "Mythic (Мифическая)"}
]

def get_random_card():
rarities = list(RARITY_DATA.keys())
weights = [data["chance"] for data in RARITY_DATA.values()]
chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
available_characters = [card for card in CARDS if card["rarity"] == chosen_rarity]
chosen_character = random.choice(available_characters)
personal_chance = RARITY_DATA[chosen_rarity]["chance"] / len(available_characters)
return chosen_character, personal_chance

def get_main_keyboard():
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn_get = types.KeyboardButton("🎴 Тянуть персонажа")
btn_bal = types.KeyboardButton("💰 Баланс и Инвентарь")
markup.add(btn_get, btn_bal)
return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
bot.send_message(
message.chat.id,
"Привет! Добро пожаловать в симулятор Vought International. Крути кейсы, продавай дубликаты и закупайся в магазине!",
reply_markup=get_main_keyboard()
)

@bot.message_handler(commands=['balance'])
@bot.message_handler(func=lambda message: message.text == "💰 Баланс и Инвентарь")
def show_balance(message):
user_id = message.from_user.id
balance = user_balances.get(user_id, 0)
inventory = user_inventories.get(user_id, [])
compounds = user_compounds.get(user_id, 0)

if not inventory:
    inv_text = "Твой ростер пуст."
else:
    from collections import Counter
    counts = Counter(inventory)
    inv_text = "\n".join([f"• {name} — {count} шт." for name, count in counts.items()])

inline_markup = types.InlineKeyboardMarkup(row_width=2)
btn_sell = types.InlineKeyboardButton("💰 Продать дубликаты", callback_data="sell_duplicates")
btn_shop = types.InlineKeyboardButton("🛒 Магазин Vought", callback_data="open_shop")
btn_use = types.InlineKeyboardButton("🧪 Юзнуть Препарат V", callback_data="use_compound")

inline_markup.add(btn_sell)
inline_markup.add(btn_shop, btn_use)

text = (
    f"💵 Твой аккаунт Vought:\n"
    f"💰 Баланс: {balance} монет\n"
    f"🧪 Препарат V в наличии: {compounds} шт.\n\n"
    f"🗃️ Твоя команда:\n{inv_text}"
)
bot.send_message(message.chat.id, text, reply_markup=inline_markup)
@bot.message_handler(commands=['get'])
@bot.message_handler(func=lambda message: message.text == "🎴 Тянуть персонажа")
def draw_card(message):
user_id = message.from_user.id
now = datetime.now()

if user_id in user_cooldowns and now < user_cooldowns[user_id]:
    time_left = user_cooldowns[user_id] - now
    hours, remainder = divmod(int(time_left.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    inline_markup = types.InlineKeyboardMarkup()
    if user_compounds.get(user_id, 0) > 0:
        inline_markup.add(types.InlineKeyboardButton("🧪 Вколоть Препарат V (Сбросить КД)", callback_data="use_compound"))
        
    bot.send_message(
        message.chat.id, 
        f"🛑 Рано! Организм еще восстанавливается.\nПодожди: {hours}ч {minutes}м {seconds}с ⏳\n\nИли используй Препарат V, чтобы сбросить таймер!",
        reply_markup=inline_markup
    )
    return

card, exact_chance = get_random_card()

if user_id not in user_balances: user_balances[user_id] = 0
if user_id not in user_inventories: user_inventories[user_id] = []

user_inventories[user_id].append(card["name"])
user_cooldowns[user_id] = now + timedelta(hours=COOLDOWN_HOURS)

bot.send_message(
    message.chat.id, 
    f"🎉 Тебе выпал персонаж:\n\n"
    f"👤 {card['name']}\n"
    f"💎 Редкость: {card['rarity']}\n"
    f"📈 Шанс выпадения: {exact_chance:.2f}%"
)
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
user_id = call.from_user.id
balance = user_balances.get(user_id, 0)
inventory = user_inventories.get(user_id, [])
compounds = user_compounds.get(user_id, 0)

if call.data == "sell_duplicates":
    if not inventory:
        bot.answer_callback_query(call.id, "Твой ростер пуст!")
        return
        
    from collections import Counter
    counts = Counter(inventory)
    duplicates = {name: count - 1 for name, count in counts.items() if count > 1}
    
    if not duplicates:
        bot.answer_callback_query(call.id, "У тебя нет дубликатов для продажи!")
        return
        
    total_profit = 0
    sold_count = 0
    
    for name, count in duplicates.items():
        card_data = next(c for c in CARDS if c["name"] == name)
        price = RARITY_DATA[card_data["rarity"]]["sell_price"]
        total_profit += price * count
        sold_count += count
        for _ in range(count):
            inventory.remove(name)
            
    user_balances[user_id] = balance + total_profit
    user_inventories[user_id] = inventory
    
    bot.answer_callback_query(call.id, f"Успешно продано {sold_count} дубликатов на сумму {total_profit} монет!")
    show_balance(call.message)

elif call.data == "open_shop":
    inline_markup = types.InlineKeyboardMarkup()
    btn_buy = types.InlineKeyboardButton(f"🧪 Купить Препарат V — {COMPOUND_PRICE} монет", callback_data="buy_compound")
    inline_markup.add(btn_buy)
    bot.send_message(call.message.chat.id, f"🛒 Магазин Vought International:\n\n🧪 Препарат V — {COMPOUND_PRICE} монет\n(Сбрасывает таймер ожидания персонажа)", reply_markup=inline_markup)

elif call.data == "buy_compound":
    if balance < COMPOUND_PRICE:
        bot.answer_callback_query(call.id, "Недостаточно монет для покупки!")
        return
        
    user_balances[user_id] = balance - COMPOUND_PRICE
    user_compounds[user_id] = compounds + 1
    bot.answer_callback_query(call.id, "Препарат V успешно куплен!")
    show_balance(call.message)

elif call.data == "use_compound":
    if user_compounds.get(user_id, 0) <= 0:
        bot.answer_callback_query(call.id, "У тебя нет Препарата V!")
        return
        
    user_compounds[user_id] = compounds - 1
    if user_id in user_cooldowns:
        del user_cooldowns[user_id]
        
    bot.answer_callback_query(call.id, "🧬 Препарат V введен! Таймер сброшен.")
    bot.send_message(call.message.chat.id, "⚡ Твой организм восстановился! Можешь снова тянуть персонажа.")
app = Flask('')

@app.route('/')
def home(): return "Бот работает!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

if name == 'main':
keep_alive()
bot.remove_webhook()
print("Бот успешно запущен!")
bot.infinity_polling()
