from aiogram import Router
import asyncio
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from database import get_user_referral_link  # Функция для получения реферальной ссылки
from database import get_referral_count, get_user_earnings,get_user_language,load_texts  # Функции для подсчёта рефералов и заработка
from config import CURRENCY  # Обозначение валюты
from messages import *  # Импортируем сообщения
texts = load_texts('texts.xlsx')
referral_router = Router()

# Кнопка "Для друзей"
@referral_router.message(lambda message: message.text and message.text.strip() in {str(texts['friends_button'].get(lang, '') or '').strip() for lang in texts['friends_button']})
async def friends_menu(message: Message):
    user_language = await get_user_language(message.from_user.id)
    buttons = [
        [KeyboardButton(text=texts['referral_link'][user_language]), KeyboardButton(text=texts['info_refferal_net'][user_language])],
        [KeyboardButton(text=texts['back_to_main_menu_button'][user_language])],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Выберите действие:", reply_markup=keyboard)

@referral_router.message(lambda message: message.text and message.text.strip() in {str(texts['referral_link'].get(lang, '') or '').strip() for lang in texts['referral_link']})
async def handle_referral_link_button(message: Message):
    user_id = message.from_user.id
    user_language = message.from_user.language_code  # Получаем язык пользователя

    # Предполагается, что эта функция возвращает ссылку
    referral_link = await get_user_referral_link(user_id)

    if referral_link:
        await message.answer(
            texts['referral_link_callback'].get(user_language, texts['referral_link_callback']['en']).format(
                referral_link=referral_link)
        )
    else:
        await message.answer(texts['referral_error_link'].get(user_language, texts['referral_error_link']['en']))

@referral_router.message(lambda message: message.text and message.text.strip() in {str(texts['info_refferal_net'].get(lang, '') or '').strip() for lang in texts['info_refferal_net']})
async def referral_network_info(message: Message):
    user_id = message.from_user.id
    user_language = await get_user_language(user_id)
    # Получаем количество приглашённых пользователей
    referral_count = await get_referral_count(user_id)

    # Используем run_in_executor для вызова синхронной функции
    loop = asyncio.get_event_loop()
    earnings = await loop.run_in_executor(None, get_user_earnings, user_id)

    # Формируем текст сообщения с переменными
    info_text = texts.get('info_promt', {}).get(user_language, 'ru')  # default_text - текст по умолчанию

    # Заменяем переменные в строке
    info_text = info_text.format(referral_count=referral_count, earnings=earnings, CURRENCY=CURRENCY)
    info_text = info_text.replace('\n\n', ' ')  # Заменяем все символы новой строки на пробелы
    await message.answer(info_text)


