# bot.py
import json
import random
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from cards import tarot_cards
from config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

HISTORY_FILE = "history.json"
STATS_FILE = "stats.json"
USER_LANG_FILE = "user_lang.json"
DAILY_LIMIT_FILE = "daily_limits.json"

# --- Локализации ---
TEXTS = {
    "en": {
        "start": "🌙✨ Welcome to Daily Tarot Bot! ✨🌙\nChoose a card or spread from the menu below:",
        "help": """
🌙 **Tarot Bot Commands** ✨

**/daily** 🌅  
`Draw your daily guidance card for today's energy`

**/random** 🎴  
`Draw a random tarot card with interpretation`

**/shuffle** 🔀  
`Shuffle the virtual deck for fresh readings`

**/meaning [card]** 📖  
`Get detailed meaning of any tarot card`  
Example: `/meaning The Fool`

💫 *Each reading is saved in your personal history* 📖
        """,
        "shuffle_success": "🔀 The deck has been shuffled!",
        "no_card_name": "❗ Please provide a card name, e.g., /meaning The Fool",
        "card_not_found": "❌ Card not found.",
        "no_history": "📖 No history yet.",
        "history_title": "📖 Your history (last 10 readings):\n\n",
        "love_spread": "💖 Love Spread:\n\n",
        "career_spread": "💼 Career Spread:\n\n",
        "menu_daily": "🎴 Daily Card",
        "menu_love": "💖 Love Spread",
        "menu_career": "💼 Career Spread",
        "menu_history": "📖 History",
        "menu_language": "🌐 Language",
        "daily_limit_reached": "⏰ You've already used your daily card today. Come back tomorrow!"
    },
    "ru": {
        "start": "🌙✨ Добро пожаловать в Таро Бота! ✨🌙\nВыберите карту или расклад из меню ниже:",
        "help": """
🌙 **Команды Таро Бота** ✨

**/daily** 🌅  
`Ваша ежедневная карта на сегодня`

**/random** 🎴  
`Случайная карта Таро с толкованием`

**/shuffle** 🔀  
`Перетасовать виртуальную колоду`

**/meaning [карта]** 📖  
`Получить значение любой карты Таро`  
Пример: `/meaning The Fool`

💫 *Каждое гадание сохраняется в вашей истории* 📖
        """,
        "shuffle_success": "🔀 Колода перетасована!",
        "no_card_name": "❗ Укажите название карты, например: /meaning The Fool",
        "card_not_found": "❌ Карта не найдена.",
        "no_history": "📖 История пока пуста.",
        "history_title": "📖 Ваша история (последние 10 гаданий):\n\n",
        "love_spread": "💖 Расклад на любовь:\n\n",
        "career_spread": "💼 Расклад на карьеру:\n\n",
        "menu_daily": "🎴 Карта Дня",
        "menu_love": "💖 Любовь",
        "menu_career": "💼 Карьера",
        "menu_history": "📖 История",
        "menu_language": "🌐 Язык",
        "daily_limit_reached": "⏰ Вы уже использовали ежедневную карту сегодня. Возвращайтесь завтра!"
    }
}

# --- Вспомогательные функции ---
def load_json(file):
    try:
        with open(file, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_json(data, file):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_lang(user_id):
    langs = load_json(USER_LANG_FILE)
    return langs.get(str(user_id), "en")

def set_user_lang(user_id, lang):
    langs = load_json(USER_LANG_FILE)
    langs[str(user_id)] = lang
    save_json(langs, USER_LANG_FILE)

def t(user_id, key):
    lang = get_user_lang(user_id)
    return TEXTS[lang].get(key, key)

def add_to_history(user_id, card_name):
    history = load_json(HISTORY_FILE)
    user_id = str(user_id)
    if user_id not in history:
        history[user_id] = []
    
    if isinstance(card_name, dict):
        card_name = card_name["en"]
    
    history[user_id].append(card_name)
    save_json(history, HISTORY_FILE)

def cleanup_history():
    history = load_json(HISTORY_FILE)
    for user_id, user_history in history.items():
        cleaned_history = []
        for item in user_history:
            if isinstance(item, dict):
                cleaned_history.append(item.get("en", str(item)))
            else:
                cleaned_history.append(str(item))
        history[user_id] = cleaned_history
    save_json(history, HISTORY_FILE)

def can_use_daily(user_id):
    daily_limits = load_json(DAILY_LIMIT_FILE)
    user_id = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user_id not in daily_limits or daily_limits[user_id] != today:
        daily_limits[user_id] = today
        save_json(daily_limits, DAILY_LIMIT_FILE)
        return True
    return False

def log_stat(command):
    stats = load_json(STATS_FILE)
    stats[command] = stats.get(command, 0) + 1
    save_json(stats, STATS_FILE)

async def send_card(message, card, user_id):
    lang = get_user_lang(user_id)
    card_name = card["name"][lang]
    card_meaning = card["meaning"][lang]
    card_text = f"🔮 {card_name}\n{card_meaning}"
    
    try:
        await message.answer_photo(
            photo=card["image"],
            caption=card_text,
            reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
        )
    except:
        await message.answer(
            card_text,
            reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
        )

# --- Кнопки ---
def main_menu(user_id):
    lang = get_user_lang(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(user_id, "menu_daily"), callback_data="daily"),
            InlineKeyboardButton(text=t(user_id, "menu_love"), callback_data="love")
        ],
        [
            InlineKeyboardButton(text=t(user_id, "menu_career"), callback_data="career"),
            InlineKeyboardButton(text=t(user_id, "menu_history"), callback_data="history")
        ],
        [
            InlineKeyboardButton(text=t(user_id, "menu_language"), callback_data="language")
        ]
    ])
    return kb

def language_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ]
    ])
    return kb

# --- Команды ---
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    await message.answer(t(user_id, "start"), reply_markup=main_menu(user_id))

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user_id = message.from_user.id
    await message.answer(t(user_id, "help"), reply_markup=main_menu(user_id))

@dp.message(Command("daily"))
async def daily_command(message: Message):
    user_id = message.from_user.id
    if not can_use_daily(user_id):
        await message.answer(t(user_id, "daily_limit_reached"))
        return
    
    card = random.choice(tarot_cards)
    add_to_history(user_id, card["name"])
    log_stat("daily")
    await send_card(message, card, user_id)

@dp.message(Command("random"))
async def random_card(message: Message):
    user_id = message.from_user.id
    card = random.choice(tarot_cards)
    add_to_history(user_id, card["name"])
    log_stat("random")
    await send_card(message, card, user_id)

@dp.message(Command("shuffle"))
async def shuffle_deck(message: Message):
    user_id = message.from_user.id
    random.shuffle(tarot_cards)
    log_stat("shuffle")
    await message.answer(
        t(user_id, "shuffle_success"),
        reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
    )

@dp.message(Command("meaning"))
async def meaning(message: Message):
    user_id = message.from_user.id
    text = message.text
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t(user_id, "no_card_name"))
        return
    
    name = parts[1].strip().lower()
    found = None
    
    found = [c for c in tarot_cards if c["name"]["en"].lower() == name]
    
    if not found:
        found = [c for c in tarot_cards if c["name"]["ru"].lower() == name]
    
    if found:
        card = found[0]
        await send_card(message, card, user_id)
    else:
        await message.answer(t(user_id, "card_not_found"))

@dp.message(Command("language"))
async def language_command(message: Message):
    await message.answer("🌐 Choose language / Выберите язык:", reply_markup=language_menu())

# --- Обработка кнопок ---
@dp.callback_query(F.data == "daily")
async def daily_handler(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        if not can_use_daily(user_id):
            await callback.message.answer(t(user_id, "daily_limit_reached"))
            await callback.answer()
            return
        
        card = random.choice(tarot_cards)
        add_to_history(user_id, card["name"])
        log_stat("daily")
        await send_card(callback.message, card, user_id)
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            print("⚠️ Old callback query ignored")
        else:
            raise e

@dp.callback_query(F.data == "love")
async def love_handler(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        cards = random.sample(tarot_cards, 3)
        for card in cards:
            add_to_history(user_id, card["name"]["en"])
        
        lang = get_user_lang(user_id)
        msg = t(user_id, "love_spread") + "\n\n"
        for c in cards:
            card_name = c["name"][lang]
            card_meaning = c["meaning"][lang]
            msg += f"🔮 {card_name} — {card_meaning}\n\n"
        
        await callback.message.answer(
            msg,
            reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
        )
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            print("⚠️ Old callback query ignored")
        else:
            raise e

@dp.callback_query(F.data == "career")
async def career_handler(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        cards = random.sample(tarot_cards, 3)
        for card in cards:
            add_to_history(user_id, card["name"]["en"])
        
        lang = get_user_lang(user_id)
        msg = t(user_id, "career_spread") + "\n\n"
        for c in cards:
            card_name = c["name"][lang]
            card_meaning = c["meaning"][lang]
            msg += f"🔮 {card_name} — {card_meaning}\n\n"
        
        await callback.message.answer(
            msg,
            reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
        )
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            print("⚠️ Old callback query ignored")
        else:
            raise e
            
@dp.callback_query(F.data == "history")
async def history_handler(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        history = load_json(HISTORY_FILE)
        user_history = history.get(str(user_id), [])
        
        if not user_history:
            await callback.message.answer(
                t(user_id, "no_history"),
                reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
            )
        else:
            lang = get_user_lang(user_id)
            translated_history = []
            for card_name in user_history[-10:]:
                found_card = None
                for card in tarot_cards:
                    if card["name"]["en"] == card_name:
                        found_card = card
                        break
                if found_card:
                    translated_history.append(found_card["name"][lang])
                else:
                    translated_history.append(card_name)
            
            msg = t(user_id, "history_title") + "\n".join(translated_history)
            await callback.message.answer(
                msg,
                reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
            )
        
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            print("⚠️ Old callback query ignored")
        else:
            raise e

@dp.callback_query(F.data.startswith("lang_"))
async def language_handler(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        lang = callback.data.split("_")[1]
        set_user_lang(user_id, lang)
        
        if lang == "en":
            msg = "🌐 Language changed to English!"
        else:
            msg = "🌐 Язык изменен на Русский!"
            
        await callback.message.answer(
            msg,
            reply_markup=main_menu(user_id)  # ← ДОБАВИТЬ МЕНЮ
        )
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            print("⚠️ Old callback query ignored")
        else:
            raise e

@dp.callback_query(F.data == "language")
async def language_menu_handler(callback: types.CallbackQuery):
    try:
        await callback.message.answer("🌐 Choose language / Выберите язык:", reply_markup=language_menu())
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            print("⚠️ Old callback query ignored")
        else:
            raise e

# --- Запуск ---
async def main():
    print("Bot is starting...")
    cleanup_history()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())