from aiogram import Router, types
from aiogram.filters import Command
from keyboards import main_keyboard

router = Router()

@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Привет! Выбери игру:", reply_markup=main_keyboard)