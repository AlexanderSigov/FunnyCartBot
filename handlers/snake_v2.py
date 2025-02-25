# handlers/snake_v2.py
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest
import random
import asyncio
import logging
from PIL import Image, ImageDraw
import io

router = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIELD_SIZE = 10
CELL_SIZE = 20  # Размер клетки в пикселях
MOVE_INTERVAL = 1.0

active_games = {}

def init_game():
    field = [[0 for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]  # 0 - пусто, 1 - змейка, 2 - еда
    snake = [(FIELD_SIZE//2, FIELD_SIZE//2)]
    field[snake[0][0]][snake[0][1]] = 1
    direction = (0, 1)
    food = spawn_food(field, snake)
    return field, snake, direction, food

def spawn_food(field, snake):
    while True:
        x = random.randint(0, FIELD_SIZE-1)
        y = random.randint(0, FIELD_SIZE-1)
        if (x, y) not in snake:
            field[x][y] = 2
            return (x, y)

def render_field(field):
    img = Image.new('RGB', (FIELD_SIZE * CELL_SIZE, FIELD_SIZE * CELL_SIZE), color='white')
    draw = ImageDraw.Draw(img)
    
    for y in range(FIELD_SIZE):
        for x in range(FIELD_SIZE):
            if field[y][x] == 1:  # Змейка
                draw.rectangle(
                    [x * CELL_SIZE, y * CELL_SIZE, (x + 1) * CELL_SIZE - 1, (y + 1) * CELL_SIZE - 1],
                    fill='green'
                )
            elif field[y][x] == 2:  # Еда
                draw.rectangle(
                    [x * CELL_SIZE, y * CELL_SIZE, (x + 1) * CELL_SIZE - 1, (y + 1) * CELL_SIZE - 1],
                    fill='red'
                )
            else:  # Пусто
                draw.rectangle(
                    [x * CELL_SIZE, y * CELL_SIZE, (x + 1) * CELL_SIZE - 1, (y + 1) * CELL_SIZE - 1],
                    fill='white',
                    outline='gray'
                )
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()

def get_keyboard():
    buttons = [
        [InlineKeyboardButton(text='⬆️', callback_data='up')],
        [InlineKeyboardButton(text='⬅️', callback_data='left'),
         InlineKeyboardButton(text='⬇️', callback_data='down'),
         InlineKeyboardButton(text='➡️', callback_data='right')],
        [InlineKeyboardButton(text='⏹ Стоп', callback_data='stop')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def game_loop(bot, user_id):
    logger.info(f"Entering game loop for user {user_id}")
    try:
        while user_id in active_games and active_games[user_id].get("running", False):
            game = active_games[user_id]
            field = game["field"]
            snake = game["snake"]
            direction = game["direction"]
            food = game["food"]
            message_id = game["message_id"]

            logger.info(f"Processing move for user {user_id}")
            head_x, head_y = snake[0]
            dx, dy = direction
            new_head = (head_x + dx, head_y + dy)

            if (new_head[0] < 0 or new_head[0] >= FIELD_SIZE or 
                new_head[1] < 0 or new_head[1] >= FIELD_SIZE or new_head in snake):
                await bot.edit_message_media(
                    chat_id=user_id,
                    message_id=message_id,
                    media=InputMediaPhoto(media=BufferedInputFile(render_field(field), filename="game_over.png")),
                    reply_markup=None
                )
                await bot.send_message(chat_id=user_id, text=f"Игра окончена! Длина: {len(snake)}")
                logger.info(f"Game over for user {user_id}: collision")
                del active_games[user_id]
                return

            snake.insert(0, new_head)
            if new_head == food:
                food = spawn_food(field, snake)
            else:
                tail = snake.pop()
                field[tail[0]][tail[1]] = 0

            field[new_head[0]][new_head[1]] = 1
            field[food[0]][food[1]] = 2

            game["field"] = field
            game["snake"] = snake
            game["food"] = food

            try:
                await bot.edit_message_media(
                    chat_id=user_id,
                    message_id=message_id,
                    media=InputMediaPhoto(media=BufferedInputFile(render_field(field), filename="snake.png")),
                    reply_markup=get_keyboard()
                )
                logger.info(f"Updated field for user {user_id}")
            except TelegramBadRequest as e:
                logger.warning(f"Failed to update message for user {user_id}: {str(e)}")
                del active_games[user_id]
                return

            await asyncio.sleep(MOVE_INTERVAL)
    except Exception as e:
        logger.error(f"Game loop crashed for user {user_id}: {str(e)}")
    logger.info(f"Game loop ended for user {user_id}")

@router.message(lambda message: message.text == "🐍 Змейка v2.0")
async def snake_start(message: Message):
    user_id = message.from_user.id
    logger.info(f"Starting Snake v2.0 for user {user_id}")
    
    if user_id in active_games:
        active_games[user_id]["running"] = False
        await asyncio.sleep(0.1)
    
    field, snake, direction, food = init_game()
    try:
        msg = await message.answer_photo(
            photo=BufferedInputFile(render_field(field), filename="snake.png"),
            reply_markup=get_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to send initial photo for user {user_id}: {str(e)}")
        return
    
    active_games[user_id] = {
        "field": field,
        "snake": snake,
        "direction": direction,
        "food": food,
        "message_id": msg.message_id,
        "running": True
    }
    
    logger.info(f"Creating game loop task for user {user_id}")
    asyncio.create_task(game_loop(message.bot, user_id))
    await message.answer(
        "Змейка v2.0 запущена!\n"
        "Зеленый - змейка, красный - еда\n"
        "Используй кнопки под картинкой для направления.\n"
        "Змейка движется сама каждые {} сек.".format(MOVE_INTERVAL)
    )

@router.callback_query(lambda c: c.data == "stop" and c.from_user.id in active_games)
async def snake_stop(callback: CallbackQuery):
    user_id = callback.from_user.id
    game = active_games[user_id]
    game["running"] = False
    await callback.bot.edit_message_media(
        chat_id=user_id,
        message_id=game["message_id"],
        media=InputMediaPhoto(media=BufferedInputFile(render_field(game["field"]), filename="game_over.png"))
    )
    await callback.bot.send_message(chat_id=user_id, text=f"Игра окончена! Длина змейки: {len(game['snake'])}")
    await callback.answer()
    del active_games[user_id]
    logger.info(f"Game stopped by user {user_id}")

@router.callback_query(lambda c: c.from_user.id in active_games)
async def snake_move(callback: CallbackQuery):
    user_id = callback.from_user.id
    game = active_games[user_id]
    
    direction_map = {
        'up': (-1, 0), 'down': (1, 0),
        'left': (0, -1), 'right': (0, 1)
    }
    
    if callback.data in direction_map:
        game["direction"] = direction_map[callback.data]
        logger.info(f"Direction changed for user {user_id} to {callback.data}")
    await callback.answer()