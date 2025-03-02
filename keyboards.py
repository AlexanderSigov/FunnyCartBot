from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Крестики-нолики"), KeyboardButton(text="🏙 Города")],
        [KeyboardButton(text="🐍 Змейка"), KeyboardButton(text="🐍 Змейка v2.0")],
        [KeyboardButton(text="😂 Генератор мемов"), KeyboardButton(text="🦖 Динозаврик")],
        [KeyboardButton(text="🎵 Угадай мелодию"), KeyboardButton(text="🎮 Pac-Man")]
    ],
    resize_keyboard=True
)

finish_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Новая игра")],
        [KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

give_up_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="😞 Сдаюсь!")]],
    resize_keyboard=True,
)

start_cities_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌍 Города мира")], 
        [KeyboardButton(text="🇷🇺 Города России")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)