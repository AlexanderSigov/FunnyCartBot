import json
import random
from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from keyboards import main_keyboard, finish_keyboard, give_up_keyboard, start_cities_keyboard

router = Router()

# 📌 Загружаем данные из JSON
with open("data/cities.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    WORLD_CITIES = {}
    for item in data["city"]:
        city_name = item["name"].strip()
        first_letter = city_name[0].upper()
        if first_letter not in WORLD_CITIES:
            WORLD_CITIES[first_letter] = []
        WORLD_CITIES[first_letter].append(city_name)

with open("data/russia-cities.json", "r", encoding="utf-8") as file:
    russia_data = json.load(file)
    RUSSIA_CITIES = {}
    for item in russia_data:
        city_name = item["name"].strip()
        first_letter = city_name[0].upper()
        if first_letter not in RUSSIA_CITIES:
            RUSSIA_CITIES[first_letter] = []
        RUSSIA_CITIES[first_letter].append(city_name)

# 📌 Активные игры {user_id: {last_letter, used_cities, cities_source, bot_limit, bot_moves}}
active_games = {}

@router.message(lambda message: message.text == "🏙 Города")
async def ask_cities_source(message: Message):
    """Спрашиваем, какие города использовать (Россия или мир)"""
    await message.answer("Выбери, какие города будем использовать:", reply_markup=start_cities_keyboard)

@router.message(lambda message: message.text in ["🌍 Города мира", "🇷🇺 Города России"])
async def ask_bot_limit(message: Message):
    """Спрашиваем лимит ответов бота"""
    user_id = message.from_user.id
    cities_source = WORLD_CITIES if message.text == "🌍 Города мира" else RUSSIA_CITIES

    active_games[user_id] = {"last_letter": None, "used_cities": set(), "cities_source": cities_source, "bot_moves": 0}
    await message.answer("Сколько раз бот может отвечать? (Напиши число, например 10)")

@router.message(lambda message: message.from_user.id in active_games and active_games[message.from_user.id].get("bot_limit") is None)
async def set_bot_limit(message: Message):
    """Устанавливаем лимит ходов бота"""
    user_id = message.from_user.id
    try:
        bot_limit = int(message.text)
        if bot_limit < 3 or bot_limit > 50:
            raise ValueError
        active_games[user_id]["bot_limit"] = bot_limit
        await message.answer("🏙️ Играем в 'Города'! Напиши первый город.", reply_markup=give_up_keyboard)
    except ValueError:
        await message.answer("❌ Введи число от 3 до 50.")

@router.message(lambda message: message.text == "😞 Сдаюсь!")
async def give_up(message: Message):
    """Игрок сдаётся"""
    user_id = message.from_user.id
    if user_id in active_games:
        del active_games[user_id]
        await message.answer("😔 Ты сдался! Бот победил. Попробуй ещё раз!", reply_markup=finish_keyboard)

@router.message(lambda message: message.text == "🔄 Новая игра")
async def new_game(message: Message):
    """Начать новую игру"""
    user_id = message.from_user.id
    if user_id in active_games:
        del active_games[user_id]
    await message.answer("🌍 Выбери режим игры:", reply_markup=start_cities_keyboard)

@router.message(lambda message: message.text == "🏠 Меню")
async def back_to_menu(message: Message):
    """Вернуться в меню"""
    user_id = message.from_user.id
    if user_id in active_games:
        del active_games[user_id]
    await message.answer("🏠 Возвращаемся в меню...", reply_markup=main_keyboard)

@router.message(lambda message: message.from_user.id in active_games)
async def process_city(message: Message):
    """Обрабатываем ввод игрока"""
    user_id = message.from_user.id
    game = active_games[user_id]
    city_input = message.text.strip()  # Оставляем исходный ввод игрока как есть

    # 🔍 Приводим к нижнему регистру для проверки без учёта регистра
    city_lower = city_input.lower()
    first_letter = city_lower[0].upper()

    # 🔍 Проверяем, начинается ли город с нужной буквы (если она задана)
    last_letter = game["last_letter"]
    if last_letter and first_letter != last_letter:
        await message.answer(f"⛔ Город должен начинаться на букву **{last_letter}**. Попробуй другой!")
        return

    # 🔍 Проверяем, был ли город уже использован (без учёта регистра)
    if city_lower in (c.lower() for c in game["used_cities"]):
        await message.answer("⛔ Этот город уже был! Попробуй другой.")
        return

    # 🔍 Проверяем, есть ли город в базе (без учёта регистра)
    cities_source = game["cities_source"]
    if first_letter not in cities_source:
        await message.answer(f"🤔 Не знаю такого города ({city_input}). Проверь правильность написания.")
        return

    # Ищем точное совпадение без учёта регистра
    matching_city = None
    for city in cities_source[first_letter]:
        if city.lower() == city_lower:
            matching_city = city  # Сохраняем оригинальный регистр из базы
            break

    if not matching_city:
        await message.answer(f"🤔 Не знаю такого города ({city_input}). Проверь правильность написания.")
        return

    # ✅ Добавляем город в использованные (в оригинальном регистре из базы)
    game["used_cities"].add(matching_city)

    # 🔍 Определяем последнюю букву (исключая 'ъ', 'ь', 'ы')
    last_letter = matching_city[-1].upper()
    while last_letter in "ЪЬЫ":
        last_letter = matching_city[-2].upper()

    game["last_letter"] = last_letter

    # 📌 Проверяем, не исчерпал ли бот свой лимит
    if game["bot_moves"] >= game["bot_limit"]:
        await message.answer("🤖 Больше не знаю городов! Ты победил! 🎉", reply_markup=finish_keyboard)
        del active_games[user_id]
        return

    # 🤖 Бот ищет город на последнюю букву
    if last_letter in cities_source:
        possible_cities = [c for c in cities_source[last_letter] if c.lower() not in (used.lower() for used in game["used_cities"])]

        # 🛑 Если городов реально нет, бот позволяет взять любую букву
        if not possible_cities:
            await message.answer(f"🤖 Я не знаю городов на букву {last_letter}. Можешь взять любую букву!")
            game["last_letter"] = None
            return

        # 📍 Если города есть, бот отвечает
        bot_city = random.choice(possible_cities)
        game["used_cities"].add(bot_city)
        game["last_letter"] = bot_city[-1].upper()
        game["bot_moves"] += 1

        while game["last_letter"] in "ЪЬЫ":
            game["last_letter"] = bot_city[-2].upper()

        await message.answer(f"📍 {bot_city}! Теперь тебе на **{game['last_letter']}**")
    else:
        await message.answer(f"🤖 Не знаю городов на {last_letter}. Бери любую букву!")
        game["last_letter"] = None