# handlers/meme_generator_v2_imgflip.py
from aiogram import Router, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import IMGFLIP_USERNAME
from config import IMGFLIP_PASSWORD
import aiohttp
import random
import logging

router = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemeGeneratorV2(StatesGroup):
    choosing_mood = State()
    top_text = State()
    bottom_text = State()

MEME_TEMPLATES = {
    "positive": [],
    "negative": [],
    "neutral": [],
    "random": []
}

async def load_templates():
    """Загружает шаблоны из Imgflip API"""
    url = "https://api.imgflip.com/get_memes"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                all_templates = [(meme["id"], meme["name"]) for meme in data["data"]["memes"]]
                MEME_TEMPLATES["positive"] = [tid for tid, name in all_templates if any(kw in name.lower() for kw in ["success", "drake", "happy", "awesome"])]
                MEME_TEMPLATES["negative"] = [tid for tid, name in all_templates if any(kw in name.lower() for kw in ["grumpy", "disaster", "problems", "bad"])]
                MEME_TEMPLATES["neutral"] = [tid for tid, name in all_templates if any(kw in name.lower() for kw in ["distracted", "philosoraptor", "troll", "forever"])]
                MEME_TEMPLATES["random"] = [tid for tid, _ in all_templates]
            else:
                logger.error(f"Failed to load templates from Imgflip: status={response.status}")
                raise Exception("Failed to load templates from Imgflip")

def get_mood_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="😊 Позитивное", callback_data="mood_positive")],
        [types.InlineKeyboardButton(text="😿 Негативное", callback_data="mood_negative")],
        [types.InlineKeyboardButton(text="😐 Нейтральное", callback_data="mood_neutral")],
        [types.InlineKeyboardButton(text="🎲 Случайно", callback_data="mood_random")],
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_skip_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip"),
         types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(lambda message: message.text == "😂 Генератор мемов")
async def start_meme_generator_v2(message: types.Message, state: FSMContext):
    await load_templates()
    await message.reply("Давай создадим мем! Выбери настроение:", reply_markup=get_mood_keyboard())
    await state.set_state(MemeGeneratorV2.choosing_mood)

@router.callback_query(lambda c: c.data == "cancel")
async def cancel_meme_generator(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Генерация мема отменена. Выбери что-то другое в меню!")
    await callback.answer()

@router.callback_query(MemeGeneratorV2.choosing_mood)
async def choose_mood(callback: types.CallbackQuery, state: FSMContext):
    if callback.data.startswith("mood_"):
        mood = callback.data.split("_")[1]
        await state.update_data(mood=mood)
        await callback.message.edit_text(
            "Введи верхний текст (или нажми 'Пропустить'):",
            reply_markup=get_skip_keyboard()
        )
        await state.set_state(MemeGeneratorV2.top_text)
        await callback.answer()

@router.message(MemeGeneratorV2.top_text)
async def get_top_text(message: types.Message, state: FSMContext):
    top_text = message.text.strip() if message.text else ""
    await state.update_data(top_text=top_text)
    await message.reply("Введи нижний текст (или нажми 'Пропустить'):", reply_markup=get_skip_keyboard())
    await state.set_state(MemeGeneratorV2.bottom_text)

@router.callback_query(MemeGeneratorV2.top_text, lambda c: c.data == "skip")
async def skip_top_text(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(top_text="")
    await callback.message.edit_text("Введи нижний текст (или нажми 'Пропустить'):", reply_markup=get_skip_keyboard())
    await state.set_state(MemeGeneratorV2.bottom_text)
    await callback.answer()

@router.message(MemeGeneratorV2.bottom_text)
async def get_bottom_text_and_generate(message: types.Message, state: FSMContext):
    bottom_text = message.text.strip() if message.text else ""
    await generate_meme(message, state, bottom_text)

@router.callback_query(MemeGeneratorV2.bottom_text, lambda c: c.data == "skip")
async def skip_bottom_text_and_generate(callback: types.CallbackQuery, state: FSMContext):
    await generate_meme(callback.message, state, "")
    await callback.answer()

async def generate_meme(message: types.Message, state: FSMContext, bottom_text: str):
    data = await state.get_data()
    mood = data["mood"]
    top_text = data["top_text"]
    template_id = random.choice(MEME_TEMPLATES[mood])

    url = "https://api.imgflip.com/caption_image"
    params = {
        "template_id": template_id,
        "username": IMGFLIP_USERNAME,
        "password": IMGFLIP_PASSWORD,
        "text0": top_text,
        "text1": bottom_text
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["success"]:
                        meme_url = data["data"]["url"]
                        logger.info(f"Generated meme: {meme_url}")
                        await message.reply_photo(photo=meme_url)
                    else:
                        logger.error(f"Imgflip API error: {data['error_message']}")
                        await message.reply("Не удалось сгенерировать мем: " + data["error_message"])
                else:
                    logger.error(f"Imgflip API failed with status: {response.status}")
                    await message.reply("Ошибка сервера Imgflip, попробуй ещё раз!")
    except Exception as e:
        logger.error(f"Exception during meme generation: {str(e)}")
        await message.reply(f"Ошибка: {str(e)}")

    await state.clear()