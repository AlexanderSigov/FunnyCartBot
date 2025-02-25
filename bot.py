import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from config import TOKEN
from handlers import start
from handlers import tic_tac_toe
from handlers import cities
from handlers import snake
from handlers import snake_v2
from handlers import meme_generator
from handlers import meme_generator_v2
from handlers import meme_generator_v2_imgflip
from handlers import dino
from handlers import guess_melody

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем объекты бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Регистрируем обработчики
dp.include_router(start.router)
dp.include_router(tic_tac_toe.router)
dp.include_router(cities.router)
dp.include_router(snake.router)
dp.include_router(snake_v2.router)
dp.include_router(meme_generator.router)
# dp.include_router(meme_generator_v2.router)
dp.include_router(meme_generator_v2_imgflip.router)
dp.include_router(dino.router)
dp.include_router(guess_melody.router)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


