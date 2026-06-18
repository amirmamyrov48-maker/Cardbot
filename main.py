```python

import os

import random

import logging

from datetime import datetime, timedelta

from threading import Thread

import telebot

from telebot import types

from flask import Flask

from dotenv import load_dotenv



# Загрузка переменных окружения

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')

bot = telebot.TeleBot(TOKEN)



# Отключаем лишние логи Flask

log = logging.getLogger('werkzeug')

log.setLevel(logging.ERROR)



# Словари для хранения данных в памяти

user_cooldowns = {}

user_balances = {}     # {user_id: баланс_монет}

user_inventories = {}   # {user_id: [список_имен_персонажей]}

user_compounds = {}     # {user_id: количество_препарата_V}



COOLDOWN_HOURS = 3

COMPOUND_PRICE = 500    # Стоимость одного Препарата V в магазине



# 1. ШАНСЫ И СТОИМОСТЬ ПРОДАЖИ ДЛЯ КАЖДОЙ РЕДКОСТИ

RARITY_DATA = {

    "Common (Обычная)": {"chance": 55.0, "sell_price": 50},

    "Rare (Редкая)": {"chance": 28.0, "sell_price": 150},

    "Epic (Эпическая)": {"chance": 12.0, "sell_price": 400},

    "Legendary (Легендарная)": {"chance": 4.2, "sell_price": 1000},

    "Mythic (Мифическая)": {"chance": 0.8, "sell_price": 5000}

}



# 2. СПИСОК ПЕРСОНАЖЕЙ

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



# --- БАЛАНС, ИНВЕНТАРЬ И УПРАВЛЕНИЕ ПРЕДМЕТАМИ ---

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



    # Создаем инлайн-меню управления

    inline_markup = types.InlineKeyboardMarkup(row_width=2)

    btn_sell = types.InlineKeyboardButton("💰 Продать дубликаты", callback_data="sell_duplicates")

    btn_shop = types.InlineKeyboardButton("🛒 Магазин Vought", callback_data="open_shop")

    btn_use = types.InlineKeyboardButton("🧪 Юзнуть Препарат V", callback_data="use_compound")

    

    inline_markup.add(btn_sell)

    inline_markup.add(btn_shop, btn_use)



    text = (

        f"💵 **Твой аккаунт Vought:**\n"

        f"💰 Баланс: `{balance}` монет\n"

        f"🧪 Препарат V в наличии: `{compounds}` шт.\n\n"

        f"🗃️ **Твоя команда:**\n{inv_text}"

    )

    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=inline_markup)



# --- ОТКРЫТИЕ КЕЙСА ---

@bot.message_handler(commands=['get'])

@bot.message_handler(func=lambda message: message.text == "🎴 Тянуть персонажа")

def draw_card(message):

    user_id = message.from_user.id

    now = datetime.now()



    if user_id in user_cooldowns and now < user_cooldowns[user_id]:

        time_left = user_cooldowns[user_id] - now

        hours, remainder = divmod(int(time_left.total_seconds()), 3600)

        minutes, seconds = divmod(remainder, 60)

        

        # Если есть кулдаун, предлагаем сразу использовать Препарат V, если он есть

        inline_markup = types.InlineKeyboardMarkup()

        if user_compounds.get(user_id, 0) > 0:

            inline_markup.add(types.InlineKeyboardButton("🧪 Вколоть Препарат V (Сбросить КД)", callback_data="use_compound"))

            

        bot.send_message(

            message.chat.id, 

            f"🛑 **Рано! Организм еще восстанавливается.**\nПодожди: `{hours}ч {minutes}м {seconds}с` ⏳\n\n"

            f"Или используй Препарат V, чтобы сбросить таймер!",

            parse_mode="Markdown",

            reply_markup=inline_markup

        )

        return



    card, exact_chance = get_random_card()

    

    # Инициализация

    if user_id not in user_balances: user_balances[user_id] = 0

    if user_id not in user_inventories: user_inventories[user_id] = []

    if user_id not in user_compounds: user_compounds[user_id] = 0

    

    user_inventories[user_id].append(card["name"])

    user_cooldowns[user_id] = now + timedelta(hours=COOLDOWN_HOURS)

    

    sell_price = RARITY_DATA[card['rarity']]['sell_price']

    

    text = (

        f"✨ **Вы открыли кейс Vought!** ✨\n\n"

        f"👤 Персонаж:\n"

        f"💎 Редкость:\n"

        f"🎯 **Шанс выпадения:** {exact_chance:.2f}%\n"

        f"💵 **Стоимость продажи:** {sell_price} монет\n\n"

        f"⏱ _Следующая бесплатная попытка через 3 часа!_"

    )

    bot.send_message(message.chat.id, text, parse_mode="Markdown")



# --- КОЛБЭКИ ИНЛАЙН-КНОПОК ---



@bot.callback_query_handler(func=lambda call: True)

def handle_callbacks(call):

    user_id = call.from_user.id

    

    # 1. Продажа дубликатов

    if call.data == "sell_duplicates":

        inventory = user_inventories.get(user_id, [])

        if not inventory:

            bot.answer_callback_query(call.id, "Твой инвентарь пуст!")

            return



        kept_items = []

        items_to_sell = []

        for item in inventory:

            if item not in kept_items: kept_items.append(item)

            else: items_to_sell.append(item)

                

        if not items_to_sell:

            bot.answer_callback_query(call.id, "У тебя нет дубликатов!", show_alert=True)

            return

            

        total_earned = 0

        for item_name in items_to_sell:

            card_data = next(c for c in CARDS if c["name"] == item_name)

            total_earned += RARITY_DATA[card_data["rarity"]]["sell_price"]

            

        user_inventories[user_id] = kept_items

        user_balances[user_id] = user_balances.get(user_id, 0) + total_earned

        

        bot.answer_callback_query(call.id, f"Продано дубликатов на {total_earned} монет!", show_alert=True)

        show_balance(call.message)



    # 2. Открыть магазин

    elif call.data == "open_shop":

        inline_markup = types.InlineKeyboardMarkup()

        btn_buy = types.InlineKeyboardButton(f"🛒 Купить 1 шт. за {COMPOUND_PRICE} монет", callback_data="buy_compound")

        btn_back = types.InlineKeyboardButton("⬅️ Назад в профиль", callback_data="back_to_profile")

        inline_markup.add(btn_buy)

        inline_markup.add(btn_back)

        

        bot.edit_message_text(

            chat_id=call.message.chat.id,

            message_id=call.message.message_id,

            text=f"🛒 **Магазин Лаборатории Vought**\n\n🧪 **Препарат V**\n"

                 f"Описание: Полностью убирает кулдаун на получение персонажа.\n"

                 f"Цена: `{COMPOUND_PRICE}` монет.\n\n"

                 f"Твой баланс: `{user_balances.get(user_id, 0)}` монет.",

            parse_mode="Markdown",

            reply_markup=inline_markup

        )



    # 3. Покупка препарата

    elif call.data == "buy_compound":

        balance = user_balances.get(user_id, 0)

        if balance < COMPOUND_PRICE:

            bot.answer_callback_query(call.id, "❌ Недостаточно монет Vought! Продай дубликаты.", show_alert=True)

            return

            

        user_balances[user_id] = balance - COMPOUND_PRICE

        user_compounds[user_id] = user_compounds.get(user_id, 0) + 1

        

        bot.answer_callback_query(call.id, "✅ Успешная покупка сыворотки!", show_alert=False)

        # Обновляем страницу магазина, чтобы обновился баланс в тексте

        handle_callbacks(types.CallbackQuery(call.id, call.from_user, call.message, 'open_shop', ''))



    # 4. Использование препарата

    elif call.data == "use_compound":

        compounds = user_compounds.get(user_id, 0)

        if compounds <= 0:

            bot.answer_callback_query(call.id, "❌ У тебя нет Препарата V! Купи его в магазине.", show_alert=True)

            return

            

        # Сбрасываем кулдаун

        if user_id in user_cooldowns:

            del user_cooldowns[user_id]

            

        user_compounds[user_id] = compounds - 1

        bot.answer_callback_query(call.id, "🧪 Препарат вколот! Силы восстановлены, кулдаун сброшен!", show_alert=True)

        

        # Перенаправляем на вызов функции выдачи карты, удалив старое сообщение о кулдауне

        bot.delete_message(call.message.chat.id, call.message.message_id)

        draw_card(call.message)



    # 5. Возврат назад

    elif call.data == "back_to_profile":

        bot.delete_message(call.message.chat.id, call.message.message_id)

        show_balance(call.message)



# Web-сервер для поддержания активности (Keep-Alive)

app = Flask('')

@app.route('/')

def home(): return "Бот работает!"



def run(): app.run(host='0.0.0.0', port=8080)

def keep_alive(): Thread(target=run).start()



if __name__ == '__main__':

    keep_alive()

    bot.remove_webhook()

    print("Бот успешно запущен!")

    bot.infinity_polling()



```
