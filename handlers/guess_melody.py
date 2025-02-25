# handlers/guess_melody_yandex.py
from aiogram import Router, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from yandex_music import Client
from config import YANDEX_TOKEN
import random
import logging
import aiohttp
import os
import asyncio
import ffmpeg
from aiogram.types import FSInputFile
from pathlib import Path

router = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем путь к ffmpeg относительно расположения проекта
BASE_DIR = Path(__file__).resolve().parent.parent  # Переходим в корень проекта (FunnyCart)
FFMPEG_BIN_DIR = BASE_DIR / "ffmpeg_bin"  # Путь к папке с ffmpeg
FFMPEG_PATH = str(FFMPEG_BIN_DIR / "ffmpeg.exe")  # Полный путь к ffmpeg

# Проверяем, существует ли ffmpeg
if not os.path.exists(FFMPEG_PATH):
    raise FileNotFoundError(f"FFmpeg не найден по пути: {FFMPEG_PATH}")

# Добавляем путь к ffmpeg в PATH
os.environ["PATH"] = str(FFMPEG_BIN_DIR) + os.pathsep + os.environ["PATH"]


client = Client(YANDEX_TOKEN).init()

class GuessMelody(StatesGroup):
    playing = State()

TRACKS = [
    "The Beatles - Yesterday",
    "Queen - Bohemian Rhapsody",
    "Adele - Rolling in the Deep",
    "Ed Sheeran - Shape of You",
    "Billie Eilish - Bad Guy",
    "Drake - Hotline Bling",
    "Dua Lipa - Don't Start Now",
    "The Weeknd - Blinding Lights",
    "Imagine Dragons - Radioactive",
    "Post Malone - Circles"
]

TRACK_DURATION = 10  # 10 секунд

async def download_and_cut_track(preview_url):
    try:
        logger.info(f"Downloading track from {preview_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(preview_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download track: HTTP {response.status}")
                    return None
                with open("temp_track.mp3", "wb") as f:
                    f.write(await response.read())
        logger.info("Track downloaded")

        if not os.path.exists("temp_track.mp3"):
            logger.error("Temp track file was not created")
            return None
        file_size = os.path.getsize("temp_track.mp3")
        if file_size == 0:
            logger.error("Temp track file is empty")
            return None

        logger.info("Cutting track")
        duration = float(ffmpeg.probe("temp_track.mp3")["format"]["duration"])
        if duration > TRACK_DURATION:
            start_point = random.uniform(0, duration - TRACK_DURATION)
        else:
            start_point = 0

        command = [
            FFMPEG_PATH,
            '-i', 'temp_track.mp3',
            '-ss', str(start_point),
            '-t', str(TRACK_DURATION),
            '-acodec', 'mp3',
            '-y',
            'cut_track.mp3'
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
            if process.returncode != 0:
                logger.error(f"FFmpeg failed: {stderr.decode().strip()}")
                return None
            # Логируем только ключевой результат
            stderr_str = stderr.decode().strip()
            if stderr_str:
                for line in stderr_str.splitlines():
                    if "size=" in line or "time=" in line or "bitrate=" in line:
                        logger.info(f"FFmpeg result: {line.strip()}")
            logger.info("Track cut completed")
        except asyncio.TimeoutError:
            logger.error("FFmpeg timed out")
            process.kill()
            await process.communicate()
            return None

        os.remove("temp_track.mp3")
        if not os.path.exists("cut_track.mp3"):
            logger.error("Cut track file was not created")
            return None
        return "cut_track.mp3"
    except Exception as e:
        logger.error(f"Error cutting track: {str(e)}")
        return None

async def get_track_options(state: FSMContext):
    data = await state.get_data()
    track_list = data.get("track_list")
    current_round = data.get("round", 1)

    if not track_list:  # Если список песен ещё не создан
        track_list = TRACKS.copy()
        random.shuffle(track_list)
        await state.update_data(track_list=track_list)

    track_query = track_list[current_round - 1]
    
    try:
        logger.info(f"Searching for track: {track_query}")
        search_result = client.search(track_query, type_="track")
        if not search_result.tracks or not search_result.tracks.results:
            logger.warning(f"No results found for track: {track_query}")
            return None, None, None
        
        track = search_result.tracks.results[0]
        download_info = track.get_download_info()
        if not download_info:
            logger.warning(f"No download info available for track: {track_query}")
            return None, None, None
        
        preview_url = download_info[0].get_direct_link()
        if not preview_url:
            logger.warning(f"No direct link available for track: {track_query}")
            return None, None, None
        
        cut_file = await download_and_cut_track(preview_url)
        if not cut_file:
            return None, None, None
        
        correct_answer = f"{track.artists[0].name} - {track.title}"
        wrong_options = random.sample([t for t in TRACKS if t != track_query], 3)
        options = [correct_answer] + wrong_options
        random.shuffle(options)
        logger.info(f"Selected track: {correct_answer}")
        return cut_file, correct_answer, options
    except Exception as e:
        logger.error(f"Error fetching track {track_query}: {str(e)}")
        return None, None, None

@router.message(lambda message: message.text == "🎵 Угадай мелодию")
async def start_guess_melody(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(GuessMelody.playing)
    await state.update_data(round=1, score=0, max_rounds=5, track_list=None)
    await next_round(message, state, user_id)

async def next_round(message: types.Message, state: FSMContext, user_id: int):
    data = await state.get_data()
    if not data:
        logger.error("State data is empty")
        await message.reply("Ошибка: данные состояния потеряны. Начни игру заново.")
        await state.clear()
        return

    current_round = data["round"]
    max_rounds = data["max_rounds"]
    score = data["score"]

    if current_round > max_rounds:
        await message.reply(f"Игра окончена! Твой счёт: {score}/{max_rounds}")
        await state.clear()
        return

    cut_file, correct_answer, options = await get_track_options(state)
    if not cut_file:
        await message.reply("Не удалось найти песню, попробуй снова!")
        await state.clear()
        return

    if not os.path.exists(cut_file) or os.path.getsize(cut_file) == 0:
        logger.error(f"File {cut_file} does not exist or is empty")
        await message.reply("Ошибка: файл с аудио не найден или пуст.")
        await state.clear()
        return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=opt, callback_data=f"answer_{i}_{correct_answer}")]
        for i, opt in enumerate(options)
    ] + [[types.InlineKeyboardButton(text="Завершить игру", callback_data="end_game")]])

    await message.reply(f"Раунд {current_round}/{max_rounds}. Угадай мелодию по отрывку! Счёт: {score}")

    logger.info("Sending voice message")
    try:
        await asyncio.wait_for(
            message.bot.send_voice(chat_id=user_id, voice=FSInputFile(cut_file), reply_markup=keyboard),
            timeout=30
        )
        logger.info("Voice sent")
        os.remove(cut_file)
        await state.update_data(correct_answer=correct_answer, options=options)
    except asyncio.TimeoutError:
        logger.error("Timeout while sending voice message")
        await message.reply("Ошибка: время отправки аудио истекло.")
        await state.clear()
    except Exception as e:
        logger.error(f"Error sending voice: {str(e)}")
        await message.reply("Ошибка при отправке аудио, попробуй снова!")
        await state.clear()

@router.callback_query(GuessMelody.playing, lambda c: c.data.startswith("answer_"))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    correct_answer = data["correct_answer"]
    current_round = data["round"]
    score = data["score"]

    callback_data = callback.data.split("_")
    chosen_index = int(callback_data[1])
    chosen_answer = data["options"][chosen_index]

    if chosen_answer == correct_answer:
        score += 1
        response = f"Правильно! Это {correct_answer}"
    else:
        response = f"Неправильно! Это была {correct_answer}, а ты выбрал {chosen_answer}"

    await callback.message.reply(response)
    await state.update_data(round=current_round + 1, score=score)
    await next_round(callback.message, state, user_id)
    await callback.answer()

@router.callback_query(GuessMelody.playing, lambda c: c.data == "end_game")
async def end_game(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data["score"]
    max_rounds = data["max_rounds"]
    await callback.message.reply(f"Игра завершена! Твой счёт: {score}/{max_rounds}")
    await state.clear()
    await callback.answer()