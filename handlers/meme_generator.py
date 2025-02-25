# handlers/meme_generator.py
from aiogram import Router, types
from aiogram.filters import Command
import aiohttp
import random

router = Router()

# Список популярных шаблонов мемов (можно расширить)
MEME_TEMPLATES = [
    "Grumpy-Cat",
    "Distracted-Boyfriend",
    "Drake-Hotline-Bling",
    "Success-Kid",
    "One-Does-Not-Simply",
]

@router.message(Command("meme"))  # Используем Command фильтр вместо commands=["meme"]
async def generate_meme(message: types.Message):
    """Генерирует мем с пользовательским текстом через apimeme.com"""
    try:
        # Разделяем текст на верхний и нижний
        text = message.text.replace("/meme", "").strip()
        if "|" not in text:
            await message.reply("Укажи текст в формате: /meme <верхний текст> | <нижний текст>")
            return
        top_text, bottom_text = [t.strip() for t in text.split("|", 1)]

        # Выбираем случайный шаблон
        template = random.choice(MEME_TEMPLATES)

        # Формируем URL для API
        url = f"http://apimeme.com/meme?meme={template}&top={top_text}&bottom={bottom_text}"

        # Отправляем запрос и получаем картинку
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    meme_image = await response.read()
                    await message.reply_photo(photo=types.BufferedInputFile(meme_image, filename="meme.jpg"))
                else:
                    await message.reply("Не удалось сгенерировать мем, попробуй ещё раз!")
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")