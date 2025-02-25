# handlers/tic_tac_toe.py
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import random

router = Router()

games = {}  # {chat_id: {"board": [[0, 0, 0], [0, 0, 0], [0, 0, 0]], "difficulty": "easy/hard/impossible"}}

def render_board(board):
    """Создает игровое поле с кнопками"""
    buttons = []
    symbols = {0: "⬜", 1: "❌", 2: "⭕"}

    for i in range(3):
        row_buttons = [
            InlineKeyboardButton(
                text=symbols[board[i][j]], callback_data=f"move_{i}_{j}"
            ) for j in range(3)
        ]
        buttons.append(row_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(lambda message: message.text == "❌ Крестики-нолики")
async def select_difficulty(message: types.Message):
    """Запрашивает выбор уровня сложности"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😎 Легкий", callback_data="difficulty_easy")],
        [InlineKeyboardButton(text="🤖 Сложный", callback_data="difficulty_hard")],
        [InlineKeyboardButton(text="💀 Невозможный", callback_data="difficulty_impossible")]
    ])
    await message.answer("Выбери уровень сложности:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("difficulty_"))
async def start_game(callback_query: types.CallbackQuery):
    """Начинает игру с выбранной сложностью"""
    difficulty = callback_query.data.split("_")[1]  # "easy", "hard" или "impossible"
    board = [[0] * 3 for _ in range(3)]
    games[callback_query.message.chat.id] = {"board": board, "difficulty": difficulty}

    difficulty_text = {"easy": "Легкий", "hard": "Сложный", "impossible": "Невозможный"}
    await callback_query.message.edit_text(
        f"Начинаем игру! Сложность: {difficulty_text[difficulty]}\nТы ходишь первым. Выбери клетку:",
        reply_markup=render_board(board)
    )

@router.callback_query(lambda c: c.data.startswith("move_"))
async def player_move(callback_query: types.CallbackQuery):
    """Обрабатывает ход игрока"""
    user_id = callback_query.message.chat.id
    if user_id not in games:
        await callback_query.answer("Игра не найдена, начни новую через меню!")
        return

    game = games[user_id]
    board = game["board"]
    _, row, col = callback_query.data.split("_")
    row, col = int(row), int(col)

    if board[row][col] != 0:
        await callback_query.answer("Эта клетка уже занята!")
        return

    board[row][col] = 1  # Ход игрока (крестик)

    if check_winner(board, 1):
        await callback_query.message.edit_text("🎉 Ты победил!", reply_markup=None)
        del games[user_id]
        return

    if is_draw(board):
        await callback_query.message.edit_text("🤝 Ничья!", reply_markup=None)
        del games[user_id]
        return

    # Ход бота (в зависимости от сложности)
    if game["difficulty"] == "easy":
        random_bot_move(board)
    elif game["difficulty"] == "hard":
        smart_bot_move(board)
    else:  # impossible
        minimax_bot_move(board)

    if check_winner(board, 2):
        await callback_query.message.edit_text("😢 Бот победил!", reply_markup=None)
        del games[user_id]
        return

    await callback_query.message.edit_text("Твой ход:", reply_markup=render_board(board))

def random_bot_move(board):
    """Простой бот с рандомными ходами"""
    empty_cells = [(i, j) for i in range(3) for j in range(3) if board[i][j] == 0]
    if empty_cells:
        row, col = random.choice(empty_cells)
        board[row][col] = 2  # Ход бота (нолик)

def smart_bot_move(board):
    """AI для бота: пытается победить, блокировать игрока или ходит оптимально"""
    empty_cells = [(i, j) for i in range(3) for j in range(3) if board[i][j] == 0]

    # 1️⃣ Проверяем, может ли бот выиграть
    for row, col in empty_cells:
        board[row][col] = 2
        if check_winner(board, 2):
            return
        board[row][col] = 0

    # 2️⃣ Проверяем, может ли игрок выиграть, и блокируем его
    for row, col in empty_cells:
        board[row][col] = 1
        if check_winner(board, 1):
            board[row][col] = 2
            return
        board[row][col] = 0

    # 3️⃣ Ходим в центр, если он свободен
    if board[1][1] == 0:
        board[1][1] = 2
        return

    # 4️⃣ Ходим в один из углов (если свободен)
    for row, col in [(0, 0), (0, 2), (2, 0), (2, 2)]:
        if board[row][col] == 0:
            board[row][col] = 2
            return

    # 5️⃣ Если ничего не получилось, делаем случайный ход
    row, col = random.choice(empty_cells)
    board[row][col] = 2

def minimax_bot_move(board):
    """Невозможный бот с алгоритмом МинМакс"""
    best_score = float('-inf')
    best_move = None
    for i in range(3):
        for j in range(3):
            if board[i][j] == 0:
                board[i][j] = 2  # Пробуем ход бота
                score = minimax(board, 0, False)
                board[i][j] = 0  # Откатываем ход
                if score > best_score:
                    best_score = score
                    best_move = (i, j)
    if best_move:
        board[best_move[0]][best_move[1]] = 2

def minimax(board, depth, is_maximizing):
    """Алгоритм МинМакс для оценки хода"""
    if check_winner(board, 2):  # Бот победил
        return 10 - depth
    if check_winner(board, 1):  # Игрок победил
        return -10 + depth
    if is_draw(board):  # Ничья
        return 0

    if is_maximizing:  # Ход бота (максимизируем)
        best_score = float('-inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == 0:
                    board[i][j] = 2
                    score = minimax(board, depth + 1, False)
                    board[i][j] = 0
                    best_score = max(score, best_score)
        return best_score
    else:  # Ход игрока (минимизируем)
        best_score = float('inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == 0:
                    board[i][j] = 1
                    score = minimax(board, depth + 1, True)
                    board[i][j] = 0
                    best_score = min(score, best_score)
        return best_score

def check_winner(board, player):
    """Проверка победителя"""
    for row in board:
        if all(cell == player for cell in row):
            return True
    for col in range(3):
        if all(board[row][col] == player for row in range(3)):
            return True
    if all(board[i][i] == player for i in range(3)) or all(board[i][2 - i] == player for i in range(3)):
        return True
    return False

def is_draw(board):
    """Проверка на ничью"""
    return all(cell != 0 for row in board for cell in row)