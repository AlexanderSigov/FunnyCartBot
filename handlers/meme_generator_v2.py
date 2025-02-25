# handlers/meme_generator_v2.py
from aiogram import Router, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiohttp
import random

router = Router()

# Определяем состояния FSM
class MemeGeneratorV2(StatesGroup):
    choosing_mood = State()  # Выбор настроения
    top_text = State()       # Ввод верхнего текста
    bottom_text = State()    # Ввод нижнего текста

# Расширенный список шаблонов с категориями настроения
MEME_TEMPLATES = {
    "positive": [
        "Success-Kid", "Drake-Hotline-Bling", "Good-Guy-Greg", "Yo-Dawg", "10-Guy",
        "Happy-Cat", "Overly-Attached-Girlfriend", "Socially-Awesome-Penguin", "Aw-Yeah-Rage-Face",
        "Chemistry-Cat", "Lol-Cat"
    ],
    "negative": [
        "Grumpy-Cat", "One-Does-Not-Simply", "Disaster-Girl", "First-World-Problems", "Bad-Luck-Brian",
        "Scumbag-Steve", "Socially-Awkward-Penguin", "Yao-Ming-Face", "Facepalm", "Rageguy-F7U12",
        "Cereal-Guy-Spitting", "Me-Gusta"
    ],
    "neutral": [
        "Distracted-Boyfriend", "Philosoraptor", "Y-U-No", "Troll-Face", "Forever-Alone",
        "Ancient-Aliens", "Spongebob-Mocking", "Skeptical-3rd-World-Child", "Okay-Guy-Rage-Face",
        "Derp"
    ],
    "random": [
        "Success-Kid", "Drake-Hotline-Bling", "Good-Guy-Greg", "Yo-Dawg", "10-Guy",
        "Happy-Cat", "Overly-Attached-Girlfriend", "Socially-Awesome-Penguin", "Aw-Yeah-Rage-Face",
        "Chemistry-Cat", "Lol-Cat",
        "Grumpy-Cat", "One-Does-Not-Simply", "Disaster-Girl", "First-World-Problems", "Bad-Luck-Brian",
        "Scumbag-Steve", "Socially-Awkward-Penguin", "Yao-Ming-Face", "Facepalm", "Rageguy-F7U12",
        "Cereal-Guy-Spitting", "Me-Gusta",
        "Distracted-Boyfriend", "Philosoraptor", "Y-U-No", "Troll-Face", "Forever-Alone",
        "Ancient-Aliens", "Spongebob-Mocking", "Skeptical-3rd-World-Child", "Okay-Guy-Rage-Face",
        "Derp"
    ]
}

def get_mood_keyboard():
    """Клавиатура для выбора настроения"""
    buttons = [
        [types.InlineKeyboardButton(text="😊 Позитивное", callback_data="mood_positive")],
        [types.InlineKeyboardButton(text="😿 Негативное", callback_data="mood_negative")],
        [types.InlineKeyboardButton(text="😐 Нейтральное", callback_data="mood_neutral")],
        [types.InlineKeyboardButton(text="🎲 Случайно", callback_data="mood_random")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_skip_keyboard():
    """Клавиатура с кнопкой Пропустить"""
    buttons = [
        [types.InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(lambda message: message.text == "😂 Генератор мемов")
async def start_meme_generator_v2(message: types.Message, state: FSMContext):
    """Запускает генератор мемов v2 через кнопку"""
    await message.reply("Давай создадим мем! Выбери настроение:", reply_markup=get_mood_keyboard())
    await state.set_state(MemeGeneratorV2.choosing_mood)

@router.callback_query(MemeGeneratorV2.choosing_mood)
async def choose_mood(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор настроения"""
    if callback.data.startswith("mood_"):
        mood = callback.data.split("_")[1]  # positive, negative, neutral, random
        await state.update_data(mood=mood)
        await callback.message.edit_text(
            "Введи верхний текст (или нажми 'Пропустить', чтобы оставить пустым):",
            reply_markup=get_skip_keyboard()
        )
        await state.set_state(MemeGeneratorV2.top_text)
        await callback.answer()
    else:
        await callback.answer("Выбери настроение из предложенных!", show_alert=True)

@router.message(MemeGeneratorV2.top_text)
async def get_top_text(message: types.Message, state: FSMContext):
    """Сохраняет верхний текст"""
    top_text = message.text.strip() if message.text else ""
    await state.update_data(top_text=top_text)
    await message.reply(
        "Введи нижний текст (или нажми 'Пропустить', чтобы оставить пустым):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MemeGeneratorV2.bottom_text)

@router.callback_query(MemeGeneratorV2.top_text, lambda c: c.data == "skip")
async def skip_top_text(callback: types.CallbackQuery, state: FSMContext):
    """Пропускает верхний текст"""
    await state.update_data(top_text="")
    await callback.message.edit_text(
        "Введи нижний текст (или нажми 'Пропустить', чтобы оставить пустым):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MemeGeneratorV2.bottom_text)
    await callback.answer()

@router.message(MemeGeneratorV2.bottom_text)
async def get_bottom_text_and_generate(message: types.Message, state: FSMContext):
    """Сохраняет нижний текст и генерирует мем"""
    bottom_text = message.text.strip() if message.text else ""
    await generate_meme(message, state, bottom_text)

@router.callback_query(MemeGeneratorV2.bottom_text, lambda c: c.data == "skip")
async def skip_bottom_text_and_generate(callback: types.CallbackQuery, state: FSMContext):
    """Пропускает нижний текст и генерирует мем"""
    await generate_meme(callback.message, state, "")
    await callback.answer()

async def generate_meme(message: types.Message, state: FSMContext, bottom_text: str):
    """Генерирует мем и отправляет его"""
    data = await state.get_data()
    mood = data["mood"]
    top_text = data["top_text"]

    # Выбираем случайный шаблон из выбранного настроения
    template = random.choice(MEME_TEMPLATES[mood])

    # Формируем URL для API
    url = f"http://apimeme.com/meme?meme={template}&top={top_text}&bottom={bottom_text}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    meme_image = await response.read()
                    await message.reply_photo(photo=types.BufferedInputFile(meme_image, filename="meme.jpg"))
                else:
                    await message.reply("Не удалось сгенерировать мем, попробуй ещё раз!")
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

    # Завершаем состояние
    await state.clear()