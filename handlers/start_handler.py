from aiogram import Router, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import connect_db, add_user, get_user_role, set_user_role,get_referral_bonus
from messages import *  # Импортируем все сообщения
from config import DEFAULT_LANGUAGE, ADMIN_ID

router = Router()

# Генерация кнопок для выбора языка
def get_language_markup():
    buttons = [
        InlineKeyboardButton(text="Русский", callback_data="language_ru"),
        InlineKeyboardButton(text="English", callback_data="language_en")
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return markup


@router.callback_query(lambda callback: callback.data.startswith("language_"))
async def process_language_selection(callback: CallbackQuery):
    selected_language = callback.data.split("_")[1]
    if selected_language == "ru":
        await callback.message.answer("Вы выбрали русский язык.")
        # Установите русский язык в настройках пользователя
    elif selected_language == "en":
        await callback.message.answer("You selected English.")
        # Установите английский язык в настройках пользователя

    await callback.answer()  # Закрываем всплывающее уведомление


@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    user = message.from_user
    user_id = user.id

    # Получаем аргументы команды /start (реферальный код)
    args = message.text.split()[1:]  # Разделяем текст и берем все после команды

    # Проверяем, зарегистрирован ли уже пользователь
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()

        if not user_exists:
            # Если пользователя нет в базе, добавляем его
            await add_user(user_id=user.id, username=user.username, first_name=user.first_name)

            # Формируем сообщение для администраторов
            admin_message = (
                f"👤 Новый пользователь зарегистрировался:\n"
                f"🆔 ID: {user.id}\n"
                f"👤 Имя: {user.first_name or 'Не указано'}\n"
                f"💬 Username: @{user.username or 'Не указан'}"
            )

            # Получаем список администраторов из базы данных
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE role = 'admin'")
                admins = cursor.fetchall()

            # Отправляем уведомление каждому администратору
            for admin in admins:
                admin_id = admin[0]  # Индекс 0, так как fetchall возвращает кортежи
                try:
                    await message.bot.send_message(chat_id=admin_id, text=admin_message)
                except Exception as e:
                    # Логируем ошибки отправки сообщений
                    print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")
            # Обрабатываем реферальную ссылку, если она есть
            if args and args[0].startswith("ref"):
                try:
                    referrer_id = int(args[0].replace("ref", ""))  # Извлекаем ID реферера
                    if referrer_id != user_id:  # Проверяем, чтобы пользователь не реферил сам себя
                        # Получаем роль реферера
                        referrer_role = await get_user_role(referrer_id)
                        if not referrer_role:
                            referrer_role = "user"  # Роль по умолчанию

                        # Получаем бонус для реферального события
                        referral_bonus = get_referral_bonus(event_type="registration", role=referrer_role)

                        # Сохраняем информацию о реферале в таблице "referrals"
                        cursor.execute(""" 
                            INSERT INTO referrals (referrer_id, referred_id)
                            VALUES (?, ?)
                        """, (referrer_id, user_id))

                        # Начисляем бонус пригласившему
                        cursor.execute("""
                            UPDATE users
                            SET balance = balance + ?
                            WHERE user_id = ?
                        """, (referral_bonus, referrer_id))
                        conn.commit()

                        await message.answer(
                            referral_registration_message_ru if DEFAULT_LANGUAGE == 'ru' else referral_registration_message_en)
                    else:
                        await message.answer(
                            referral_error_message_ru if DEFAULT_LANGUAGE == 'ru' else referral_error_message_en)
                except ValueError:
                    await message.answer(
                        invalid_referral_code_message_ru if DEFAULT_LANGUAGE == 'ru' else invalid_referral_code_message_en)
            else:
                await message.answer(
                    registration_success_message_ru if DEFAULT_LANGUAGE == 'ru' else registration_success_message_en)

        else:
            await message.answer(
                already_registered_message_ru if DEFAULT_LANGUAGE == 'ru' else already_registered_message_en)

    # Получаем роль пользователя
    user_role = await get_user_role(message.from_user.id)

    # Обычное меню
    menu_buttons = [
        [KeyboardButton(text="Продукты"), KeyboardButton(text="Для друзей")],
        [KeyboardButton(text="Баланс"), KeyboardButton(text="Партнеры")],
        [KeyboardButton(text="Инфо"), KeyboardButton(text="Личный кабинет")],
    ]
    if user_role == 'admin' or user.id == int(ADMIN_ID):
        menu_buttons.append([KeyboardButton(text="Админ панель")])
    menu_markup = ReplyKeyboardMarkup(keyboard=menu_buttons, resize_keyboard=True)

    # Отправляем приветственное сообщение с меню
    await message.answer(
        "Добро пожаловать! Выберите действие из меню ниже.",
        reply_markup=menu_markup
    )

    # Сохраняем данные о пользователе
    await state.set_state("main_menu")
    await state.update_data(language=DEFAULT_LANGUAGE)  # Устанавливаем язык по умолчанию

    # Если пользователь не имеет роли, назначаем роль по умолчанию
    role = await get_user_role(user.id)
    if not role:
        await set_user_role(user.id, "user")  # Назначаем роль "user" по умолчанию


@router.message(lambda message: message.text == "Русский")
async def set_russian(message: Message, state: FSMContext):
    # Обновляем язык в состоянии
    await message.answer("Вы выбрали русский язык.")
    await state.update_data(language="ru")

    # Выполняем дальнейшую логику на основе выбранного языка
    await continue_registration(message, state)


@router.message(lambda message: message.text == "English")
async def set_english(message: Message, state: FSMContext):
    # Обновляем язык в состоянии
    await message.answer("You selected English.")
    await state.update_data(language="en")

    # Выполняем дальнейшую логику на основе выбранного языка
    await continue_registration(message, state)


async def continue_registration(message: Message, state: FSMContext):
    # Получаем язык из состояния
    data = await state.get_data()
    user_language = data.get("language", "en")  # По умолчанию английский

    # Логика, которая зависит от выбранного языка
    if user_language == 'ru':
        await message.answer("Добро пожаловать! Регистрация завершена.")  # Пример сообщения на русском
    else:
        await message.answer("Welcome! Registration is complete.")  # Пример сообщения на английском
