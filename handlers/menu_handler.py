from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID
from database import get_random_aphorism, get_user_role, get_random_image, get_user_language,load_texts
router = Router()
# Функция для загрузки текстов
texts = load_texts('texts.xlsx')
@router.message(lambda message: message.text and message.text.strip() in {str(texts['back_to_main_menu_button'].get(lang, '') or '').strip() for lang in texts['back_to_main_menu_button']})
async def back_to_main_menu(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        user_language = await get_user_language(user_id)

        # Проверка кнопки "Назад в главное меню"
        user_role = await get_user_role(user_id)
        user_state = await state.get_state()
        print(f'Состояние пользователя: {user_state}')

        # Генерация афоризма
        aphorism = get_random_aphorism()
        aphorism_text = f"«{aphorism[0]}»\n© {aphorism[1]}" if aphorism else "Вы вернулись в главное меню."

        # Генерация случайного изображения
        image_file_id = get_random_image()

        # Клавиатура для главного меню
        menu_buttons = [
            [KeyboardButton(text=texts['products_button'][user_language]),
             KeyboardButton(text=texts['friends_button'][user_language])],
            [KeyboardButton(text=texts['balance_button'][user_language]),
             KeyboardButton(text=texts['partners_button'][user_language])],
            [KeyboardButton(text=texts['info_button'][user_language]),
             KeyboardButton(text=texts['personal_account'][user_language])],
            [KeyboardButton(text="🏠")]  # Кнопка Домик
        ]

        if user_role == 'admin' or user_id == int(ADMIN_ID):
            menu_buttons.append([KeyboardButton(text=texts['admin_panel_button'][user_language])])

        menu_markup = ReplyKeyboardMarkup(keyboard=menu_buttons, resize_keyboard=True, one_time_keyboard=False)

        # Отправка изображения или текста с афоризмом
        if image_file_id:
            await message.answer_photo(photo=image_file_id, caption=aphorism_text, reply_markup=menu_markup)
        else:
            await message.answer(aphorism_text, reply_markup=menu_markup)

        # Сброс состояния после завершения действия
        await state.clear()

    except Exception as e:
        print(f"Ошибка в обработчике: {e}")

# Обработчик для кнопки "Домик 🏠"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['home_button'].get(lang, '') or '').strip() for lang in texts['home_button']})
async def home_button_handler(message: Message):
    # Удаляем сообщение с текстом "🏠 Домик"
    await message.delete()

    # Получаем случайный афоризм
    aphorism = get_random_aphorism()
    aphorism_text = f"«{aphorism[0]}»\n© {aphorism[1]}" if aphorism else "Афоризмы пока не были сгенерированы."

    # Получаем случайное изображение (если есть)
    image_file_id = get_random_image()

    # Отправка афоризма с изображением или текстом
    if image_file_id:
        await message.answer_photo(
            photo=image_file_id,
            caption=aphorism_text
        )
    else:
        await message.answer(aphorism_text)
# dlya jazika
