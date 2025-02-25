# handlers/snake_v2.py
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import random
import asyncio
import logging

router = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIELD_SIZE = 10
SNAKE = '🟩'  # Зеленый квадрат для змейки
FOOD = '🟥'   # Красный квадрат для еды
EMPTY = '⬜'  # Белый квадрат для пустого пространства
MOVE_INTERVAL = 0.8  # Оставляем ваш интервал

active_games = {}

def init_game():
    field = [[EMPTY for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]
    snake = [(FIELD_SIZE//2, FIELD_SIZE//2)]
    field[snake[0][0]][snake[0][1]] = SNAKE
    direction = (0, 1)  # Начальное направление (вправо)
    food = spawn_food(field, snake)
    pending_direction = None  # Буфер для следующего направления
    score = 0  # Начальный счёт
    return field, snake, direction, food, pending_direction, score

def spawn_food(field, snake):
    while True:
        x = random.randint(0, FIELD_SIZE-1)
        y = random.randint(0, FIELD_SIZE-1)
        if (x, y) not in snake:
            field[x][y] = FOOD
            return (x, y)

def render_field(field, score):
    return f"Очки: {score}\n```\n" + '\n'.join(''.join(row) for row in field) + "\n```"

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
            pending_direction = game["pending_direction"]
            score = game["score"]
            message_id = game["message_id"]

            # Применяем отложенное направление, если есть
            if pending_direction is not None:
                new_direction = pending_direction
                # Проверяем, не разворот ли это (180 градусов)
                if (new_direction[0] != -direction[0] or new_direction[1] != -direction[1]):
                    direction = new_direction
                    logger.info(f"Applied pending direction for user {user_id}: {direction}")
                else:
                    logger.info(f"Ignored 180-degree turn for user {user_id}: {new_direction}")
                game["pending_direction"] = None  # Сбрасываем буфер

            logger.info(f"Processing move for user {user_id}")
            head_x, head_y = snake[0]
            dx, dy = direction
            new_head = (head_x + dx, head_y + dy)

            if (new_head[0] < 0 or new_head[0] >= FIELD_SIZE or 
                new_head[1] < 0 or new_head[1] >= FIELD_SIZE or new_head in snake):
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=f"Игра окончена! Длина: {len(snake)}, Очки: {score}"
                )
                logger.info(f"Game over for user {user_id}: collision")
                del active_games[user_id]
                return

            snake.insert(0, new_head)
            if new_head == food:
                score += 5  # Увеличиваем счёт при поедании еды
                food = spawn_food(field, snake)
            else:
                tail = snake.pop()
                field[tail[0]][tail[1]] = EMPTY

            field[new_head[0]][new_head[1]] = SNAKE
            field[food[0]][food[1]] = FOOD

            game["field"] = field
            game["snake"] = snake
            game["direction"] = direction
            game["food"] = food
            game["score"] = score

            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=render_field(field, score),
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

@router.message(lambda message: message.text == "🐍 Змейка")
async def snake_start(message: Message):
    user_id = message.from_user.id
    logger.info(f"Starting Snake for user {user_id}")
    
    if user_id in active_games:
        active_games[user_id]["running"] = False
        await asyncio.sleep(0.1)
    
    field, snake, direction, food, pending_direction, score = init_game()
    try:
        msg = await message.answer(
            render_field(field, score),
            reply_markup=get_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to send initial field for user {user_id}: {str(e)}")
        return
    
    active_games[user_id] = {
        "field": field,
        "snake": snake,
        "direction": direction,
        "food": food,
        "pending_direction": pending_direction,
        "score": score,
        "message_id": msg.message_id,
        "running": True
    }
    
    logger.info(f"Creating game loop task for user {user_id}")
    asyncio.create_task(game_loop(message.bot, user_id))
    await message.answer(
        "Змейка запущена!\n"
        "🟩 - змейка, 🟥 - еда, ⬜ - пусто\n"
        "Используй кнопки для направления (без разворота на 180°).\n"
        "Змейка движется каждые {} сек, +5 очков за еду.".format(MOVE_INTERVAL)
    )

@router.callback_query(lambda c: c.data == "stop" and c.from_user.id in active_games)
async def snake_stop(callback: CallbackQuery):
    user_id = callback.from_user.id
    game = active_games[user_id]
    game["running"] = False
    await callback.bot.edit_message_text(
        chat_id=user_id,
        message_id=game["message_id"],
        text=f"Игра окончена! Длина змейки: {len(game['snake'])}, Очки: {game['score']}"
    )
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
        game["pending_direction"] = direction_map[callback.data]
        logger.info(f"Pending direction changed for user {user_id} to {callback.data}")
    await callback.answer()

if __name__ == "__main__":
    pass