import pandas as pd
from aiogram import Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.state import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database import save_feedback_to_db, get_user_language,load_texts
router = Router()


class FeedbackState(StatesGroup):
    waiting_for_feedback = State()


# Функция загрузки текста из Excel
texts = load_texts('texts.xlsx')


# Главное меню информации
@router.message(lambda message: message.text and message.text.strip() in {str(texts['info_button'].get(lang, '') or '').strip() for lang in texts['info_button']})
async def info_main_menu(message: Message):
    user_language =await get_user_language(message.from_user.id)  # Получаем язык пользователя

    buttons = [
        [KeyboardButton(text=texts["about_button"][user_language]),
         KeyboardButton(text=texts["rules_button"][user_language])],
        [KeyboardButton(text=texts["feedback_button"][user_language]),
         KeyboardButton(text=texts["partners_button"][user_language])],
        [KeyboardButton(text=texts["back_to_main_menu_button"][user_language])],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer(texts['info_menu_prompt'][user_language], reply_markup=keyboard)


# Подменю "О нас"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['about_button'].get(lang, '') or '').strip() for lang in texts['about_button']})
async def about_us(message: Message):
    about_text = texts.get('about_text', "Информация о нас не доступна.")
    await message.answer(about_text, disable_web_page_preview=True)


# Подменю "Правила"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['rules_button'].get(lang, '') or '').strip() for lang in texts['rules_button']})
async def rules(message: Message):
    rules_text = texts.get('rules_text', "Правила не доступны.")
    await message.answer(rules_text, disable_web_page_preview=True)


# Подменю "Обратная связь"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['feedback_button'].get(lang, '') or '').strip() for lang in texts['feedback_button']})
async def feedback(message: Message):
    feedback_text = texts.get('feedback_text', "Информация по обратной связи не доступна.")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.get("write_support_button", "Написать в поддержку"),
                                  callback_data="write_feedback")]
        ],
        row_width=1
    )

    await message.answer(feedback_text, reply_markup=keyboard, disable_web_page_preview=True)


# Обработчик нажатия на кнопку "Написать в поддержку"
@router.callback_query(lambda c: c.data == "write_feedback")
async def write_feedback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Оповещение, что кнопка была нажата
    await callback_query.message.answer(texts.get('write_feedback_prompt', "Пожалуйста, напишите ваше обращение:"))
    await state.set_state(FeedbackState.waiting_for_feedback)  # Используем await state.set_state()


# Обработчик получения обращения
@router.message(StateFilter(FeedbackState.waiting_for_feedback))
async def save_feedback(message: Message, state: FSMContext):
    feedback_text = message.text
    await save_feedback_to_db(message.from_user.id, feedback_text)
    await message.answer(
        texts.get('feedback_received', "Ваше обращение отправлено в поддержку. Мы скоро свяжемся с вами."))

    # Завершение состояния
    await state.clear()  # Завершаем состояние, чтобы вернуться к обычному режиму
