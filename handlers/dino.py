# handlers/dino.py
from aiogram import Router, types
import asyncio
import random
import logging

router = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
FIELD_WIDTH = 10
FIELD_HEIGHT = 3
DINO = "🦖"
CACTUS = "🌵"
BIRD = "🐦"
EMPTY = "⬜"
GROUND = "_"
MOVE_INTERVAL = 0.5  # Начальный интервал обновления (сек)
MIN_OBSTACLE_GAP = 3  # Минимальное расстояние между препятствиями
ENABLE_ACCELERATION = True  # Включение/выключение ускорения
ACCELERATION_RATE = 0.02  # Уменьшение интервала за шаг (сек)
ACCELERATION_INTERVAL = 5  # Ускорение каждые 5 очков (быстрее, чем 10)
MIN_MOVE_INTERVAL = 0.2  # Минимальный интервал (сек)

active_games = {}

def init_game():
    field = [[EMPTY for _ in range(FIELD_WIDTH)] for _ in range(FIELD_HEIGHT)]
    field[FIELD_HEIGHT-1][0] = DINO  # Динозавр на нижней строке (2,0)
    obstacles = [(FIELD_HEIGHT-1, FIELD_WIDTH-1, "cactus")]  # Начальный кактус
    jumping = False
    jump_timer = 0
    pending_jump = False
    score = 0
    move_interval = MOVE_INTERVAL
    return field, obstacles, jumping, jump_timer, pending_jump, score, move_interval

def render_field(field, score):
    return f"Счёт: {score}\n" + "\n".join("".join(row) for row in field) + "\n" + GROUND * FIELD_WIDTH

def get_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬆️ Прыжок", callback_data="jump"),
         types.InlineKeyboardButton(text="⏹ Стоп", callback_data="stop")]
    ])

@router.message(lambda message: message.text == "🦖 Динозаврик")
async def dino_start(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_games:
        active_games[user_id]["running"] = False
        await asyncio.sleep(0.1)
    
    field, obstacles, jumping, jump_timer, pending_jump, score, move_interval = init_game()
    msg = await message.answer(render_field(field, score), reply_markup=get_keyboard())
    
    active_games[user_id] = {
        "field": field,
        "obstacles": obstacles,
        "jumping": jumping,
        "jump_timer": jump_timer,
        "pending_jump": pending_jump,
        "score": score,
        "move_interval": move_interval,
        "message_id": msg.message_id,
        "running": True
    }
    
    logger.info(f"Started game for user {user_id} with move_interval={move_interval}")
    asyncio.create_task(dino_loop(message.bot, user_id))
    await message.answer("Динозаврик запущен! Используй 'Прыжок' для управления.")

async def dino_loop(bot, user_id):
    logger.info(f"Entering Dino loop for user {user_id}")
    try:
        while user_id in active_games and active_games[user_id]["running"]:
            game = active_games[user_id]
            field = game["field"]
            obstacles = game["obstacles"]
            jumping = game["jumping"]
            jump_timer = game["jump_timer"]
            pending_jump = game["pending_jump"]
            score = game["score"]
            move_interval = game["move_interval"]
            message_id = game["message_id"]

            # Обновляем прыжок
            if jump_timer > 0:
                jump_timer -= 1
                if jump_timer == 0:
                    field[0][0] = EMPTY
                    field[2][0] = DINO
                    jumping = False
                    logger.info(f"Dino landed for user {user_id} at position (2,0)")
                    if pending_jump:
                        field[2][0] = EMPTY
                        field[0][0] = DINO
                        jumping = True
                        jump_timer = 2
                        pending_jump = False
                        logger.info(f"Buffered jump executed for user {user_id}, moved to (0,0)")
            elif pending_jump and not jumping:
                field[2][0] = EMPTY
                field[0][0] = DINO
                jumping = True
                jump_timer = 2
                pending_jump = False
                logger.info(f"Buffered jump executed for user {user_id}, moved to (0,0)")

            game["jump_timer"] = jump_timer
            game["jumping"] = jumping
            game["pending_jump"] = pending_jump

            # Двигаем препятствия
            new_obstacles = []
            for row, col, obst_type in obstacles:
                field[row][col] = EMPTY
                new_col = col - 1
                if new_col >= 0:
                    if field[row][new_col] == DINO:
                        await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=f"Игра окончена! Счёт: {score}")
                        logger.info(f"Collision detected for user {user_id} at position ({row},{new_col}), Type: {obst_type}, Score: {score}")
                        del active_games[user_id]
                        return
                    field[row][new_col] = CACTUS if obst_type == "cactus" else BIRD
                    new_obstacles.append((row, new_col, obst_type))
                else:
                    logger.info(f"{obst_type.capitalize()} removed for user {user_id} at left edge")

            obstacles = new_obstacles

            # Добавляем новое препятствие с проверкой расстояния
            if (random.random() < 0.2 and 
                not any(o[1] >= FIELD_WIDTH - MIN_OBSTACLE_GAP for o in obstacles)):
                if random.random() < 0.6:  # 60% шанс на кактус
                    obstacles.append((FIELD_HEIGHT-1, FIELD_WIDTH-1, "cactus"))
                    field[FIELD_HEIGHT-1][FIELD_WIDTH-1] = CACTUS
                    logger.info(f"New cactus added for user {user_id} at position ({FIELD_HEIGHT-1},{FIELD_WIDTH-1})")
                else:  # 40% шанс на птицу
                    obstacles.append((0, FIELD_WIDTH-1, "bird"))
                    field[0][FIELD_WIDTH-1] = BIRD
                    logger.info(f"New bird added for user {user_id} at position (0,{FIELD_WIDTH-1})")

            # Устанавливаем динозавра на правильную позицию, если он не прыгает
            if not jumping and field[2][0] != DINO:
                field[2][0] = DINO
                logger.info(f"Dino repositioned for user {user_id} at (2,0)")

            score += 1
            if ENABLE_ACCELERATION and score % ACCELERATION_INTERVAL == 0:
                new_interval = max(move_interval - ACCELERATION_RATE, MIN_MOVE_INTERVAL)
                if new_interval != move_interval:
                    move_interval = new_interval
                    logger.info(f"Speed increased for user {user_id}, new move_interval={move_interval}")
            game["move_interval"] = move_interval
            game["field"] = field
            game["obstacles"] = obstacles
            game["score"] = score

            await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=render_field(field, score), reply_markup=get_keyboard())
            await asyncio.sleep(move_interval)
    except Exception as e:
        logger.error(f"Dino loop crashed for user {user_id}: {str(e)}")
    finally:
        if user_id in active_games:
            del active_games[user_id]

@router.callback_query(lambda c: c.data == "stop" and c.from_user.id in active_games)
async def dino_stop(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = active_games[user_id]
    game["running"] = False
    await callback.bot.edit_message_text(chat_id=user_id, message_id=game["message_id"], text=f"Игра окончена! Счёт: {game['score']}")
    await callback.answer()
    logger.info(f"Game stopped by user {user_id}")
    del active_games[user_id]

@router.callback_query(lambda c: c.data == "jump" and c.from_user.id in active_games)
async def dino_jump(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = active_games[user_id]
    logger.info(f"Jump requested by user {user_id}, jumping={game['jumping']}, timer={game['jump_timer']}, pending={game['pending_jump']}, dino_pos={game['field'][2][0]}")
    if not game["jumping"] and game["field"][2][0] == DINO:
        game["field"][2][0] = EMPTY
        game["field"][0][0] = DINO
        game["jumping"] = True
        game["jump_timer"] = 2
        logger.info(f"Jump executed for user {user_id}, moved to (0,0)")
    else:
        game["pending_jump"] = True
        logger.info(f"Jump buffered for user {user_id}")
    await callback.answer()