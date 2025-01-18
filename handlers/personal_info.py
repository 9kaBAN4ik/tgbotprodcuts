from aiogram import Router, types, F
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID
from aiogram.filters import Command, CommandStart, StateFilter, BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,InlineKeyboardButton,InlineKeyboardMarkup,CallbackQuery,Message,ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (get_user_courses, get_course_progress, get_user_products,get_user_role,get_product_by_id,
                      get_user_purchase_for_product,is_partner,is_admin,get_courses_by_partner,get_lessons_for_course,
                      add_question,get_partner_products,get_users_by_product_partner,get_lessons_by_course_id,
                      get_lesson_by_id,get_questions_by_lesson_id,get_question_by_id,get_user_by_id,get_product_by_id_for_purchases,
                      get_lesson_by_id_for_purchase,get_product_and_partner_by_id,get_partner_by_product_id,insert_partner_question,
                      mark_question_as_answered,get_unanswered_questions_by_partner,get_question_from_user_by_id,get_question_from_user_by_product_and_question_id,
                      get_user_progress,update_user_progress,get_next_question_id,create_user_progress,get_next_question_in_lesson,
                      connect_db,update_user_language,load_texts,get_user_language,get_course_by_id,add_course,add_lesson,get_random_image,get_random_aphorism)# Функции для работы с БД
import logging
import json
from handlers.menu_handler import back_to_main_menu
# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

texts = load_texts("texts.xlsx")

router = Router()
class PartnerFilter(BaseFilter):
    async def __call__(self, message: types.Message):
        # Проверяем, является ли пользователь партнёром или администратором
        return await is_partner(message.from_user.id) or await is_admin(message.from_user.id)
class AskPartnerState(StatesGroup):
    waiting_for_message = State()

class waitPartnerAnswer(StatesGroup):
    waiting_for_answer = State()

class QuestionStates(StatesGroup):
    waiting_for_course_selection = State()
    waiting_for_lesson_selection = State()
    waiting_for_question_text = State()
    waiting_for_options = State()
    waiting_for_correct_option = State()
    waiting_for_more_questions = State()

class BroadcastState(StatesGroup):
    waiting_for_product_choice = State()
    waiting_for_message = State()

async def update_state_and_ask(
    message: types.Message,
    state: FSMContext,
    key: str,
    value: str,
    next_question: str,
    next_state: str
):
    await state.update_data({key: value})
    await message.answer(next_question)
    await state.set_state(next_state)


@router.message(
    lambda message: message.text and message.text.strip() in {str(texts['personal_account'].get(lang, '') or '').strip()
                                                              for lang in texts['personal_account']})
async def personal_info_menu(message: types.Message, state: FSMContext):
    user_role = await get_user_role(message.from_user.id)
    user_language = await get_user_language(message.from_user.id)

    buttons = [
        [KeyboardButton(text=texts['purchases_button'][user_language]),
         KeyboardButton(text=texts['donations_button'][user_language])],
        [KeyboardButton(text=texts['participate_in_the_lottery_button'][user_language]),
         KeyboardButton(text=texts['tickets_button'][user_language])],
        [KeyboardButton(text=texts['language_button'][user_language])],
    ]

    if user_role == 'partner' or user_role == 'admin':
        buttons.append([KeyboardButton(text=texts['add_lesson_button'][user_language]),
                        KeyboardButton(text=texts['add_question_button'][user_language])])
        buttons.append([KeyboardButton(text=texts['products_partner_button'][user_language]),
                        KeyboardButton(text=texts['questions_button'][user_language])])

    buttons.append([KeyboardButton(text=texts['back_to_main_menu_button'][user_language])])

    # Указываем 'keyboard' как обязательное поле
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    if user_language == "ru":
        await message.answer("Выберите интересующий раздел:", reply_markup=keyboard)
    else :
        await message.answer("Select the section you are interested in:", reply_markup=keyboard)


@router.message(lambda message: message.text and message.text.strip() in {str(texts['purchases_button'].get(lang, '') or '').strip() for lang in texts['purchases_button']})
async def show_purchases(message: types.Message):
    """Отображение списка приобретённых курсов и продуктов."""
    user_language = await get_user_language(message.from_user.id)
    user_id = message.from_user.id
    courses = get_user_courses(user_id)  # Получаем список курсов из БД
    products = get_user_products(user_id)  # Получаем список продуктов из БД

    if not courses and not products:
        await message.answer(texts['no_purchases'].get(user_language, texts['no_purchases']['en']))
        return

    buttons = []

    # Добавляем кнопки для курсов
    if courses:
        buttons.extend([InlineKeyboardButton(text=f"📘 Курс: {course['title']}", callback_data=f"course_{course['id']}") for course in courses])

    # Добавляем кнопки для продуктов
    if products:
        if user_language == "ru" :
            buttons.extend([InlineKeyboardButton(text=f"🛒 Продукт: {product['name']}", callback_data=f"product_{product['id']}") for product in products])
        else :
            buttons.extend(
                [InlineKeyboardButton(text=f"🛒 Products: {product['name']}", callback_data=f"product_{product['id']}")
                 for product in products])


    # Преобразуем кнопки в инлайн клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])  # Здесь добавляем inline_keyboard
    await message.answer(
        texts['purchases_list'].get(user_language, texts['purchases_list']['en']),
        reply_markup=keyboard
    )


@router.callback_query(lambda query: query.data.startswith("product_"))
async def product_info(query: types.CallbackQuery, state: FSMContext):
    product_id = query.data.split("_")[1]
    user_language = await get_user_language(query.from_user.id)
    product = get_product_by_id_for_purchases(product_id)
    if not product:
        if user_language == "ru":
            await query.answer("Продукт не найден.")
            return
        else :
            await query.answer("Product not found.")
            return

    if user_language == "ru":
        # Стартовое сообщение с основной информацией о продукте
        product_info = f"🛒 <b>Продукт:</b> {product['name']}\n"
        product_info += f"<b>Описание:</b> {product.get('description', 'Описание отсутствует')}\n"
        product_info += f"<b>Цена:</b> {product['price']} VED\n"
        if product.get('category'):
            product_info += f"<b>Категория:</b> {product['category']}\n"
        if product.get('code'):
            product_info += f"<b>Код продукта:</b> {product['code']}\n"
        if product.get('after_purchase'):
            product_info += f"<b>После покупки:</b> {product['after_purchase']}\n"

        # Сохраняем данные о продукте в состоянии FSM
        await state.update_data(product_info=product_info, product_id=product_id)

        # Проверка на образовательный модуль
        course_id = product.get('course_id')
        if course_id:
            lessons = get_lessons_by_course_id(course_id)

            if not lessons:
                await query.message.answer("Для этого продукта нет уроков.")
                await query.answer()
                return

            lesson_buttons = [
                InlineKeyboardButton(text=lesson[2], callback_data=f"lesson_{lesson[0]}")
                for lesson in lessons if isinstance(lesson, tuple) and len(lesson) >= 4
            ]

            if lesson_buttons:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[button] for button in lesson_buttons])
                await query.message.answer("Выберите урок для прохождения:", reply_markup=keyboard, parse_mode="HTML")
            else:
                await query.message.answer("Нет доступных уроков для этого курса.")
        else:
            # Если у продукта есть изображение, отправляем его, иначе просто информацию
            if product.get("image"):
                await query.message.answer_photo(photo=product["image"], caption=product_info, parse_mode="HTML")
            else:
                await query.message.answer(product_info, parse_mode="HTML")

    elif user_language == "en":
        # Starting message with main product information
        product_info = f"🛒 <b>Product:</b> {product['name']}\n"
        product_info += f"<b>Description:</b> {product.get('description', 'Description not available')}\n"
        product_info += f"<b>Price:</b> {product['price']} VED\n"
        if product.get('category'):
            product_info += f"<b>Category:</b> {product['category']}\n"
        if product.get('code'):
            product_info += f"<b>Product Code:</b> {product['code']}\n"
        if product.get('after_purchase'):
            product_info += f"<b>After purchase:</b> {product['after_purchase']}\n"

        # Save product information in FSM state
        await state.update_data(product_info=product_info, product_id=product_id)

        # Check for educational module
        course_id = product.get('course_id')
        if course_id:
            lessons = get_lessons_by_course_id(course_id)

            if not lessons:
                await query.message.answer("There are no lessons available for this product.")
                await query.answer()
                return

            lesson_buttons = [
                InlineKeyboardButton(text=lesson[2], callback_data=f"lesson_{lesson[0]}")
                for lesson in lessons if isinstance(lesson, tuple) and len(lesson) >= 4
            ]

            if lesson_buttons:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[button] for button in lesson_buttons])
                await query.message.answer("Select a lesson to proceed:", reply_markup=keyboard, parse_mode="HTML")
            else:
                await query.message.answer("No lessons available for this course.")
        else:
            # If the product has an image, send it; otherwise, just send the information
            if product.get("image"):
                await query.message.answer_photo(photo=product["image"], caption=product_info, parse_mode="HTML")
            else:
                await query.message.answer(product_info, parse_mode="HTML")

    await query.answer()


@router.callback_query(lambda query: query.data.startswith("lesson_"))
async def lesson_info(query: types.CallbackQuery):
    """Обработка нажатия на урок."""
    lesson_id = query.data.split("_")[1]  # Извлекаем ID урока из callback_data
    lesson = get_lesson_by_id_for_purchase(lesson_id)  # Получаем урок по ID
    user_language = await get_user_language(query.from_user.id)

    if not lesson:
        if user_language == "ru":
            await query.answer("Урок не найден.")
        else:
            await query.answer("Lesson not found.")
        return

    lesson_info = f"<b>Урок:</b> {lesson['title']}\n"
    lesson_info += f"<b>Описание:</b> {lesson.get('description', 'Описание отсутствует')}\n"

    # Создаем кнопку "Начать обучение" через InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Начать обучение", callback_data=f"start_lesson_{lesson_id}")
    keyboard.adjust(1)  # Устанавливаем ширину ряда кнопок

    if user_language == "ru":
        await query.message.answer(
            lesson_info,
            reply_markup=keyboard.as_markup(),  # Преобразование в InlineKeyboardMarkup
            parse_mode="HTML"
        )
    else:  # Для английского языка
        lesson_info_en = f"<b>Lesson:</b> {lesson['title']}\n"
        lesson_info_en += f"<b>Description:</b> {lesson.get('description', 'Description not available')}\n"

        await query.message.answer(
            lesson_info_en,
            reply_markup=keyboard.as_markup(),  # Преобразование в InlineKeyboardMarkup
            parse_mode="HTML"
        )

    await query.answer()  # Подтверждение нажатия на кнопку



@router.callback_query(lambda query: query.data.startswith("start_lesson_"))
async def start_lesson(query: types.CallbackQuery, state: FSMContext):
    """Начало прохождения урока."""

    lesson_id = query.data.split("_")[2]  # Извлекаем ID урока
    questions = get_questions_by_lesson_id(lesson_id)  # Получаем вопросы для урока
    user_language = await get_user_language(query.from_user.id)
    if not questions:
        await query.answer("Вопросы для этого урока не найдены." if user_language == "ru" else "No questions found for this lesson.")
        return

    # Извлекаем user_id и product_id из состояния FSMContext
    data = await state.get_data()
    user_id = query.from_user.id  # Получаем user_id из query
    product_id = data.get("product_id")

    if not product_id:
        await query.answer("Не удалось получить данные о продукте." if user_language == "ru" else "Failed to get product data.")
        return

    # Получаем прогресс пользователя из базы данных
    conn = connect_db()  # Создаем подключение
    cursor = conn.cursor()

    cursor.execute(
        "SELECT current_question_id FROM user_progress WHERE user_id = ? AND lesson_id = ?",
        (user_id, lesson_id)
    )
    user_progress = cursor.fetchone()  # Получаем результат запроса

    conn.close()  # Закрываем соединение

    if user_progress:
        # Если прогресс есть, начинаем с вопроса, на котором остановился пользователь
        current_question_id = user_progress[0]
    else:
        # Если прогресса нет, начинаем с первого вопроса
        current_question_id = 1

    # Получаем текущий вопрос из списка вопросов
    current_question = next((q for q in questions if q['id'] == current_question_id), None)

    if not current_question:
        await query.answer("Ошибка при получении вопроса." if user_language == "ru" else "Error fetching the question.")
        return

    # Извлекаем текст вопроса и варианты ответа
    question_text = f"<b>Вопрос:</b> {current_question['text']}\n" if user_language == "ru" else f"<b>Question:</b> {current_question['text']}\n"
    options = json.loads(current_question['options'])  # Преобразуем JSON-строку обратно в список

    # Создание кнопок для вариантов ответов
    buttons = [
        [InlineKeyboardButton(text=option, callback_data=f"answer_{current_question['id']}_{option}")]
        for option in options
    ]

    # Добавление кнопки "Вопрос партнёру"
    buttons.append([InlineKeyboardButton(
        text="Вопрос партнёру" if user_language == "ru" else "Ask partner",
        callback_data=f"ask_{product_id}_{current_question['id']}")
    ])

    # Создание клавиатуры
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await query.message.answer(
        question_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await query.answer()  # Подтверждение нажатия на кнопку



@router.callback_query(lambda query: query.data.startswith("answer_"))
async def answer_question(query: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос."""
    data = await state.get_data()
    product_id = data.get("product_id")  # Получаем ID продукта
    question_id, answer = query.data.split("_")[1:3]  # Извлекаем ID вопроса и выбранный ответ

    question = get_question_by_id(question_id)  # Получаем вопрос по ID

    if not question:
        await query.message.answer("Вопрос не найден.")
        return

    correct_answer = question['correct_answer']

    # Логируем ответы для диагностики
    print(f"Полученный ответ: {answer}, Правильный ответ: {correct_answer}")

    # Получаем информацию о прогрессе пользователя
    user_id = query.from_user.id
    user_progress = get_user_progress(user_id)
    print(f"User progress data: {user_progress}")
    # Проверяем, что прогресс существует
    if user_progress is None:
        # Если прогресс не найден, создаем его
        create_user_progress(user_id, product_id, question['lesson_id'])  # Передаем product_id и lesson_id при создании прогресса
        user_progress = get_user_progress(user_id)  # Получаем прогресс снова

    # Проверяем, что текущий вопрос относится к правильному уроку
    if question['lesson_id'] != user_progress['lesson_id']:
        await query.message.answer("Этот вопрос не относится к текущему уроку. Начните с правильного урока.")
        return

    # Если ответ правильный, обновляем прогресс
    if str(answer) == str(correct_answer):
        next_question = get_next_question_in_lesson(question['lesson_id'], question['id'])

        if next_question:
            question_text = f"<b>Вопрос:</b> {next_question.get('text', 'Текст вопроса отсутствует')}\n"

            # Удаляем кавычки и квадратные скобки из вариантов ответа
            options = next_question['options']
            cleaned_options = [option.strip('[]" ') for option in options]

            # Создание кнопок для вариантов ответов
            buttons = [
                [InlineKeyboardButton(text=option, callback_data=f"answer_{next_question['id']}_{option}")]
                for option in cleaned_options
            ]

            buttons.append([InlineKeyboardButton(
                text="Вопрос партнёру",
                callback_data=f"ask_{user_progress['product_id']}_{next_question['id']}")])

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await query.message.answer(
                question_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            # Обновляем прогресс с учётом lesson_id
            update_user_progress(user_id, next_question['id'], user_progress['product_id'], question['lesson_id'])
        else:
            await query.message.answer("Поздравляем, вы прошли все вопросы!")
    else:
        # Если ответ неправильный, даем возможность попробовать снова
        await query.message.answer("Неправильный ответ, попробуйте снова.")

    await query.answer()  # Подтверждение нажатия на кнопку


@router.callback_query(lambda query: query.data.startswith("ask_"))
async def ask_partner(query: types.CallbackQuery, state: FSMContext):
    logging.debug("Обработчик вызван для кнопки с данными: %s", query.data)

    # Разделяем данные из callback_data
    data = query.data.split("_")

    if len(data) < 3:
        await query.answer("Некорректные данные для запроса.")
        return

    product_id = data[1]  # Получаем product_id
    question_id = data[2]  # Получаем question_id

    logging.debug(f"Получены данные: product_id={product_id}, question_id={question_id}")

    # Сохраняем product_id и question_id в состоянии
    await state.update_data(product_id=product_id, question_id=question_id)

    # Запрашиваем у пользователя текст сообщения
    await query.message.answer("Пожалуйста, введите ваше сообщение для партнёра:")

    # Переходим в состояние ожидания сообщения
    await state.set_state(AskPartnerState.waiting_for_message)


import logging

# Настройка логирования для отладки
logger = logging.getLogger(__name__)


from database import insert_partner_question  # Импортируем функцию для сохранения вопроса

@router.message(AskPartnerState.waiting_for_message)
async def process_message_for_partner(message: types.Message, state: FSMContext):
    user_message = message.text

    # Извлекаем данные из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    question_id = data.get("question_id")

    # Получаем информацию о продукте
    product = get_product_by_id_for_purchases(product_id)
    if not product:
        await message.answer("Продукт не найден.")
        await state.clear()
        return

    partner_id = product.get('partner_id')
    if not partner_id:
        await message.answer("Продукт не связан с партнёром.")
        await state.clear()
        return

    question = get_question_by_id(question_id)
    if not question:
        await message.answer("Вопрос не найден.")
        await state.clear()
        return

    # Сохранение вопроса в базе данных
    insert_partner_question(
        user_id=message.from_user.id,
        partner_id=partner_id,
        product_id=product_id,
        question_id=question_id,
        question_text=question['text'],
        user_message=user_message
    )

    # Уведомляем партнёра
    partner_message = (
        f"Вопрос от пользователя по продукту {product['name']}:\n\n"
        f"Вопрос: {question['text']}\n"
        f"Сообщение от пользователя: {user_message}\n\n"
        f"Вы можете ответить на этот вопрос позже, используя команду из меню 'Поступившие вопросы'."
    )
    await message.bot.send_message(partner_id, partner_message)

    await message.answer("Ваше сообщение отправлено партнёру.")
    await state.clear()



# Обработчик кнопки курса
@router.message(lambda message: any(
    course["title"].lower() in message.text.lower() for course in get_user_courses(message.from_user.id)))
async def show_course_progress(message: types.Message):
    """Отображение прогресса по выбранному курсу."""
    user_id = message.from_user.id
    course_title = message.text
    course = next(course for course in get_user_courses(user_id) if course["title"] == course_title)
    progress = get_course_progress(user_id, course["id"])  # Получаем прогресс из БД

    if not progress:
        await message.answer(MESSAGES["personal_info"]["no_progress"])
        return

    # Формируем текст с прогрессом
    text = (
        f"📚 {progress['course_title']}\n\n"
        f"Уроков пройдено: {progress['completed_lessons']}/{progress['total_lessons']}\n"
        f"Вопросов пройдено: {progress['completed_questions']}/{progress['total_questions']}"
    )
    await message.answer(text)

@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_question_button'].get(lang, '') or '').strip() for lang in texts['add_question_button']})
async def add_question_command(message: types.Message, state: FSMContext):
    partner_id = message.from_user.id
    courses = await get_courses_by_partner(partner_id)

    if not courses:
        await message.answer("У вас пока нет созданных курсов. Сначала создайте курс с помощью команды /add_course.")
        return

    lessons = []
    for course in courses:
        lessons.extend(await get_lessons_for_course(course["id"]))  # Используем уже готовую функцию

    if not lessons:
        await message.answer("У вас пока нет уроков. Сначала создайте уроки.")
        return

    buttons = [
        InlineKeyboardButton(text=lesson["title"], callback_data=f"select_lesson_{lesson['id']}")
        for lesson in lessons
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+2] for i in range(0, len(buttons), 2)])
    await message.answer("Выберите урок, к которому хотите добавить вопрос:", reply_markup=keyboard)
    await state.set_state(QuestionStates.waiting_for_lesson_selection)



# 2. Обработка выбора урока
@router.callback_query(lambda c: c.data.startswith("select_lesson_"))
async def handle_lesson_selection(callback_query: CallbackQuery, state: FSMContext):
    lesson_id = int(callback_query.data.split("_")[2])
    await state.update_data(selected_lesson_id=lesson_id)

    await callback_query.message.answer("Введите текст вопроса:")
    await state.set_state(QuestionStates.waiting_for_question_text)


# 3. Обработка текста вопроса
@router.message(StateFilter(QuestionStates.waiting_for_question_text))
async def process_question_text(message: types.Message, state: FSMContext):
    question_text = message.text
    await state.update_data(question_text=question_text)

    await message.answer("Введите варианты ответа через запятую (не более трех):")
    await state.set_state(QuestionStates.waiting_for_options)


# 4. Обработка ввода вариантов ответа
@router.message(StateFilter(QuestionStates.waiting_for_options))
async def process_options(message: Message, state: FSMContext):
    options = message.text.split(",")
    if len(options) > 3:
        await message.answer("Можно указать не более трех вариантов. Попробуйте снова.")
        return

    await state.update_data(options=options)

    await message.answer("Введите номер правильного ответа (1, 2 или 3):")
    await state.set_state(QuestionStates.waiting_for_correct_option)


# 5. Обработка правильного ответа
@router.message(StateFilter(QuestionStates.waiting_for_correct_option))
async def process_correct_option(message: Message, state: FSMContext):
    try:
        correct_option = int(message.text)
        if correct_option not in [1, 2, 3]:
            raise ValueError

        await state.update_data(correct_option=correct_option)
        data = await state.get_data()

        # Сохраняем вопрос в базу данных
        await add_question(
            question_text=data["question_text"],  # Используйте question_text вместо text
            options=",".join(data["options"]),
            correct_answer=correct_option,
            lesson_id=data["selected_lesson_id"]
        )

        await message.answer("Вопрос успешно добавлен!")

        # Спрашиваем, хочет ли пользователь добавить ещё вопрос
        await message.answer("Хотите добавить ещё один вопрос? Ответьте 'да' или 'нет'.")
        await state.set_state(QuestionStates.waiting_for_more_questions)

    except ValueError:
        await message.answer("Введите корректный номер ответа (1, 2 или 3).")


# 6. Обработка продолжения добавления вопросов
@router.message(StateFilter(QuestionStates.waiting_for_more_questions))
async def process_more_questions(message: types.Message, state: FSMContext):
    if message.text.lower() in ["да", "yes"]:
        await message.answer("Введите текст следующего вопроса:")
        await state.set_state(QuestionStates.waiting_for_question_text)
    else:
        await message.answer("Добавление вопросов завершено.")
        await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['products_partner_button'].get(lang, '') or '').strip() for lang in texts['products_partner_button']})
async def start_broadcast_process(message: Message, state: FSMContext):
    partner_id = message.from_user.id
    print(f"Партнёр {partner_id} запросил рассылку по продукту.")

    # Получаем список продуктов партнёра
    products = get_partner_products(partner_id)
    if not products:
        await message.answer("У вас нет продуктов для рассылки.")
        print(f"Партнёр {partner_id} не имеет продуктов для рассылки.")
        return

    # Формируем кнопки с продуктами
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=f"{product['id']} : {product['name']}",
                callback_data=f"broadcast_{product['id']}"
            )]
            for product in products
        ]
    )

    print(f"Партнёр {partner_id} имеет следующие продукты для рассылки: {', '.join([product['name'] for product in products])}.")

    await message.answer("Выберите продукт для рассылки:", reply_markup=keyboard)
    await state.set_state(BroadcastState.waiting_for_product_choice)


@router.callback_query(F.data.startswith("broadcast_"))
async def broadcast_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    partner_id = callback.from_user.id
    print(f"Партнёр {partner_id} выбрал продукт с ID: {product_id} для рассылки.")

    # Сохраняем данные партнёра и продукта в FSM
    print(f"Сохранение состояния с product_id: {product_id}, partner_id: {partner_id}")
    await state.update_data(product_id=product_id, partner_id=partner_id)

    current_state = await state.get_data()
    print(f"Текущее состояние: {current_state}")

    # Получаем список пользователей, которым будет отправлена рассылка
    users_to_notify = get_users_by_product_partner(partner_id, product_id)

    if not users_to_notify:
        await callback.answer("Нет пользователей, для которых можно отправить рассылку.")
        print(f"Нет пользователей для рассылки по продукту {product_id}.")
        return

    # Просим пользователя ввести сообщение для рассылки
    await callback.answer("Напишите сообщение для рассылки.")
    await callback.message.answer("Пожалуйста, введите текст сообщения для рассылки пользователям.")

    # Устанавливаем состояние ожидания сообщения
    await state.set_state(BroadcastState.waiting_for_message)
    print("Состояние установлено: BroadcastState.waiting_for_message")

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@router.message(BroadcastState.waiting_for_message)
async def send_broadcast(message: Message, state: FSMContext):
    try:
        # Логируем текущее состояние
        current_state = await state.get_state()
        logger.debug(f"Текущее состояние: {current_state}")

        # Логируем содержимое состояния
        data = await state.get_data()
        logger.debug(f"Данные состояния при отправке сообщения: {data}")

        product_id = data.get('product_id')
        partner_id = data.get('partner_id')

        # Логируем полученные значения
        logger.debug(f"Текущее состояние product_id: {product_id}")
        logger.debug(f"Текущее состояние partner_id: {partner_id}")

        # Логируем данные перед проверкой
        if not product_id:
            logger.error(f"Ошибка: не удалось получить product_id. Данные состояния: {data}")
        if not partner_id:
            logger.error(f"Ошибка: не удалось получить partner_id. Данные состояния: {data}")

        if not product_id and not partner_id:
            logger.debug("Ошибка: не удалось получить данные для рассылки.")
            await message.answer("Ошибка: не удалось получить данные для рассылки.")
            await state.clear()  # Очищаем состояние, чтобы избежать несоответствий
            return

        # Логируем успешное извлечение данных
        logger.debug(f"Полученные данные: product_id={product_id}, partner_id={partner_id}")

        text_to_send = message.text
        logger.debug(f"Текст для рассылки: {text_to_send}")

        if not text_to_send:
            await message.answer("Вы не написали текст для рассылки.")
            return

        # Получаем пользователей, купивших продукт
        users = get_users_by_product_partner(partner_id, product_id)
        # Удаляем дублирующихся пользователей
        users = list({user['user_id']: user for user in users}.values())
        logger.debug(f"Уникальные пользователи для продукта {product_id}: {users}")

        if not users:
            await message.answer("Никто ещё не купил этот продукт.")
            await state.clear()
            return

        sent_count = 0
        logger.debug(f"Начинаем отправку сообщений {len(users)} пользователям")
        for user in users:
            try:
                logger.debug(f"Отправка сообщения пользователю {user['user_id']} с текстом: {text_to_send}")
                await message.bot.send_message(chat_id=user['user_id'], text=text_to_send)
                sent_count += 1
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {user['user_id']}: {e}")
                await message.answer(f"Ошибка при отправке сообщения пользователю {user['user_id']}: {str(e)}")

        await message.answer(f"Сообщение отправлено {sent_count} пользователям.")
    except Exception as e:
        logger.error(f"Ошибка при рассылке сообщений: {e}")
        await message.answer("Произошла ошибка при выполнении рассылки.")
    finally:
        await state.clear()  # Обязательно очищаем состояние в любом случае


@router.message(lambda message: message.text and message.text.strip() in {str(texts['questions_button'].get(lang, '') or '').strip() for lang in texts['questions_button']})
async def show_incoming_questions(message: types.Message, state: FSMContext):
    try:
        partner_id = message.from_user.id  # ID партнёра совпадает с chat_id
        logging.debug(f"Партнёр с ID {partner_id} запросил поступившие вопросы.")

        # Получаем вопросы из БД
        questions = get_unanswered_questions_by_partner(partner_id)
        logging.debug(f"Полученные вопросы для партнёра {partner_id}: {questions}")

        if not questions:
            logging.info(f"У партнёра {partner_id} нет новых вопросов.")
            await message.answer("У вас нет новых вопросов.")
            return

        # Генерируем список вопросов с кнопками
        keyboard = InlineKeyboardBuilder()
        for q in questions:
            button_text = f"Вопрос по продукту ID {q['product_id']}: {q['question_text'][:30]}..."
            logging.debug(f"Создание кнопки для вопроса с ID {q['id']} и текстом: {button_text}")
            keyboard.button(text=button_text, callback_data=f"funny:{q['product_id']}:{q['id']}")

        keyboard.adjust(1)  # Регулируем количество кнопок в ряду (1 кнопка на строку)
        logging.debug(f"Кнопки для вопросов сгенерированы: {keyboard.as_markup()}")

        # Сохраняем первый вопрос в состоянии для дальнейшей обработки
        await state.update_data(product_id=questions[0]['product_id'], question_id=questions[0]['id'], question_text=questions[0]['question_text'])
        logging.debug(f"Вопрос сохранён в состоянии: {questions[0]}")

        await message.answer("Поступившие вопросы:", reply_markup=keyboard.as_markup())
        logging.info(f"Сообщение с вопросами отправлено партнёру с ID {partner_id}")

    except Exception as e:
        logging.error(f"Ошибка в show_incoming_questions: {e}")
        await message.answer("Произошла ошибка при получении вопросов.")


@router.callback_query(lambda c: c.data.startswith("funny:"))
async def answer_question_callback(callback_query: CallbackQuery, state: FSMContext):
    logging.debug(f"Получен callback_query с данными: {callback_query.data}")

    try:
        # Разбор callback данных
        data = callback_query.data.split(":")
        if len(data) != 3 or not data[1].isdigit() or not data[2].isdigit():
            raise ValueError(f"Некорректные данные callback_query: {callback_query.data}")

        action = data[0]  # например, 'answer_question_two'
        product_id = int(data[1])  # ID продукта
        question_id = int(data[2])  # ID вопроса

        # Логирование полученных данных
        logging.debug(f"Данные из callback: Product ID: {product_id}, Question ID: {question_id}")

        # Сохранение данных в состоянии
        await state.update_data(product_id=product_id, question_id=question_id)
        logging.debug(f"Данные сохранены в состоянии: {await state.get_data()}")

        # Проверка состояния перед отправкой ответа
        question = get_question_from_user_by_product_and_question_id(product_id, question_id)
        if not question:
            logging.error(f"Вопрос с ID {question_id} и product_id {product_id} не найден в базе данных.")
            await callback_query.message.answer("Вопрос не найден.")
            await state.clear()
            return

        # Отправляем ответ пользователю
        user_id = question['user_id']
        question_text = question['question_text']
        logging.debug(f"Отправка ответа пользователю с ID {user_id}. Вопрос: {question_text}")

        await callback_query.message.answer("Введите ваш ответ на вопрос.")
        await state.set_state(waitPartnerAnswer.waiting_for_answer)  # переход в состояние ожидания ответа
        logging.debug("Перешли в состояние 'waiting_for_answer'.")

    except Exception as e:
        logging.error(f"Ошибка в обработке callback: {e}")
        await callback_query.message.answer("Произошла ошибка при обработке вашего запроса.")

@router.message(waitPartnerAnswer.waiting_for_answer)
async def process_answer_to_question(message: Message, state: FSMContext):
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        logging.debug(f"Полученные данные из состояния: {data}")

        product_id = data.get("product_id")  # Получаем product_id из состояния
        question_id = data.get("question_id")
        answer_text = message.text
        logging.debug(f"product_id={product_id}, question_id={question_id}, answer_text={answer_text}")

        if not question_id:
            logging.warning(f"В состоянии отсутствует question_id для сообщения: {message.text}")
            await message.answer("Произошла ошибка. Попробуйте ещё раз.")
            await state.clear()
            return

        # Логирование перед запросом вопроса
        logging.debug(f"Передаем в функцию get_question_from_user_by_product_and_question_id product_id={product_id}, question_id={question_id}")
        question = get_question_from_user_by_product_and_question_id(product_id, question_id)
        logging.debug(f"Результат get_question_from_user_by_product_and_question_id({product_id}, {question_id}): {question}")

        if not question:
            logging.warning(f"Вопрос с ID {question_id} и product_id {product_id} не найден в базе данных.")
            await message.answer("Вопрос не найден.")
            await state.clear()
            return

        # Отправляем ответ пользователю
        user_id = question['user_id']
        question_text = question['question_text']
        logging.debug(f"Отправка ответа пользователю с ID {user_id}. Вопрос: {question_text}, Ответ: {answer_text}")

        await message.bot.send_message(
            user_id,
            f"Ответ на ваш вопрос по продукту:\n\n{question_text}\n\nОтвет: {answer_text}"
        )
        logging.info(f"Ответ отправлен пользователю с ID {user_id}")

        # Обновляем статус вопроса
        mark_question_as_answered(question_id)
        logging.info(f"Вопрос с ID {question_id} помечен как отвеченный.")

        await message.answer("Ответ отправлен пользователю.")
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка в process_answer_to_question: {e}")
        await message.answer("Произошла ошибка при отправке ответа.")
        await state.clear()

class LotteryStates(StatesGroup):
    awaiting_ticket_number = State()

@router.message(lambda message: message.text and message.text.strip() in {str(texts['participate_in_the_lottery_button'].get(lang, '') or '').strip() for lang in texts['participate_in_the_lottery_button']})
async def participate_lottery(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, ticket_price FROM lottery WHERE active = 1")
        lottery = cursor.fetchone()

        if not lottery:
            await message.reply("Сейчас нет активных лотерей.")
            return

        lottery_id, ticket_price = lottery

        # Проверяем наличие неиспользованного билета "Повторная попытка" для текущей лотереи
        cursor.execute(
            """
            SELECT ticket_number FROM lottery_tickets 
            WHERE lottery_id = ? AND user_id = ? AND prize = 'Повторная попытка' AND used = 0
            """,
            (lottery_id, user_id)
        )
        retry_ticket = cursor.fetchone()

        if retry_ticket:
            await message.reply(
                "У вас есть неиспользованный билет 'Повторная попытка'. Введите номер нового билета, который хотите выбрать (1-1000):")
            await state.update_data(lottery_id=lottery_id, ticket_price=0, retry_ticket_number=retry_ticket[0])
        else:
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

            if not user or user[0] < ticket_price:
                await message.reply("Недостаточно средств на балансе для покупки билета.")
                return

            await message.reply("Введите номер билета, который хотите купить (1-1000):")
            await state.update_data(lottery_id=lottery_id, ticket_price=ticket_price, retry_ticket_number=None)

        await state.set_state(LotteryStates.awaiting_ticket_number)

@router.message(LotteryStates.awaiting_ticket_number)
async def process_ticket_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    ticket_number = int(message.text)

    if not 1 <= ticket_number <= 1000:
        await message.reply("Неверный номер билета. Введите номер от 1 до 1000.")
        return

    data = await state.get_data()
    lottery_id = data['lottery_id']
    ticket_price = data['ticket_price']
    retry_ticket_number = data.get('retry_ticket_number')

    with connect_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT ticket_number FROM lottery_tickets WHERE lottery_id = ? AND ticket_number = ? AND user_id IS NULL",
            (lottery_id, ticket_number)
        )
        ticket = cursor.fetchone()

        if not ticket:
            await message.reply("Этот билет уже куплен. Попробуйте выбрать другой.")
            return

        if retry_ticket_number:
            # Отметить билет "Повторная попытка" как использованный
            cursor.execute(
                "UPDATE lottery_tickets SET used = 1 WHERE ticket_number = ? AND lottery_id = ?",
                (retry_ticket_number, lottery_id)
            )
        elif ticket_price > 0:
            cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (ticket_price, user_id)
            )

        cursor.execute(
            "UPDATE lottery_tickets SET user_id = ?, username = ? WHERE ticket_number = ? AND lottery_id = ?",
            (user_id, username, ticket_number, lottery_id)
        )
        conn.commit()

    await state.clear()
    await message.reply(f"Вы успешно приобрели билет #{ticket_number}.")


@router.message(lambda message: message.text and message.text.strip() in {str(texts['tickets_button'].get(lang, '') or '').strip() for lang in texts['tickets_button']})
async def view_my_tickets(message: types.Message):
    user_id = message.from_user.id

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT lt.ticket_number, lt.prize 
            FROM lottery_tickets lt
            JOIN lottery l ON lt.lottery_id = l.id
            WHERE lt.user_id = ? AND l.active = 1
            """,
            (user_id,)
        )
        tickets = cursor.fetchall()

    if tickets:
        response = "\n".join([f"Билет #{ticket[0]}: {ticket[1]}" for ticket in tickets])
    else:
        response = "У вас пока нет билетов в активных лотереях."

    await message.reply(response)

class DonationState(StatesGroup):
    waiting_for_lottery_choice = State()
    waiting_for_amount = State()

@router.message(lambda message: message.text and message.text.strip() in {str(texts['donations_button'].get(lang, '') or '').strip() for lang in texts['donations_button']})
async def donate_to_fund(message: types.Message, state: FSMContext):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM lottery WHERE active = 1")
        active_lotteries = cursor.fetchall()

    if not active_lotteries:
        await message.reply("Сейчас нет активных лотерей для пожертвований.")
        return

    buttons = [types.KeyboardButton(text=lottery[1]) for lottery in active_lotteries]

    keyboard = types.ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True)

    await message.reply("Выберите лотерею для пожертвования:", reply_markup=keyboard)
    await state.set_state(DonationState.waiting_for_lottery_choice)
    await state.update_data(lotteries=active_lotteries)


@router.message(DonationState.waiting_for_lottery_choice)
async def process_lottery_choice(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lotteries = data['lotteries']
    lottery_choice = message.text

    selected_lottery = next((lottery for lottery in lotteries if lottery[1] == lottery_choice), None)

    if selected_lottery:
        await state.update_data(selected_lottery_id=selected_lottery[0])
        await message.reply(
            "Введите сумму пожертвования (целое число):",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(DonationState.waiting_for_amount)
    else:
        await message.reply("Пожалуйста, выберите одну из предложенных лотерей.")

@router.message(DonationState.waiting_for_amount)
async def process_donation_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError("Некорректная сумма.")

        data = await state.get_data()
        lottery_id = data['selected_lottery_id']

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE lottery SET fund = fund + ? WHERE id = ?",
                (amount, lottery_id)
            )
            conn.commit()

        await message.reply(f"Спасибо за пожертвование в размере {amount} VED!")
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректную сумму (целое число больше нуля):")


# Обработчик для команды "Сменить язык"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['language_button'].get(lang, '') or '').strip() for lang in texts['language_button']})
async def change_language(message: types.Message):
    # Создаём инлайн-кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="English", callback_data="set_lang_en")]
    ])

    await message.answer("Выберите язык / Choose your language:", reply_markup=keyboard)


# Обработчик для инлайн-кнопок смены языка

# Обработчик для команды "Сменить язык"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['language_button'].get(lang, '') or '').strip() for lang in texts['language_button']})
async def change_language(message: types.Message):
    # Создаём инлайн-кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="English", callback_data="set_lang_en")]
    ])

    await message.answer("Выберите язык / Choose your language:", reply_markup=keyboard)


# Обработчик для инлайн-кнопок смены языка
# Обработчик для инлайн-кнопок смены языка
@router.callback_query(lambda callback_query: callback_query.data.startswith("set_lang_"))
async def set_language(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    language = "ru" if callback_query.data == "set_lang_ru" else "en"

    # Обновляем язык пользователя в базе данных
    update_user_language(user_id, language)

    await callback_query.answer("Язык успешно изменён." if language == "ru" else "Language changed successfully.")
    await callback_query.message.edit_reply_markup()  # Удаляем кнопки после выбора

    # Отправляем пользователя в главное меню
    user_language = language  # Используем выбранный язык
    user_role = await get_user_role(user_id)  # Получаем роль пользователя

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

    menu_markup = ReplyKeyboardMarkup(keyboard=menu_buttons, resize_keyboard=True)

    # Отправка изображения или текста с афоризмом
    if image_file_id:
        await callback_query.message.answer_photo(photo=image_file_id, caption=aphorism_text, reply_markup=menu_markup)
    else:
        await callback_query.message.answer(aphorism_text, reply_markup=menu_markup)






@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_lesson_button'].get(lang, '') or '').strip() for lang in texts['add_lesson_button']})
async def add_lesson_command(message: types.Message, state: FSMContext):
    partner_id = message.from_user.id
    courses = await get_courses_by_partner(partner_id)
    if not courses:
        await message.answer("У вас пока нет созданных курсов. Сначала создайте курс с помощью команды /add_course.")
        return
    for course in courses:
        print(course)
    buttons = [
        InlineKeyboardButton(
            text=course.get("name", "Без названия"),
            callback_data=f"select_course_{course['id']}"
        )
        for course in courses
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    await message.answer("Выберите курс, к которому хотите добавить урок:", reply_markup=keyboard)
    await state.set_state("waiting_for_course_selection")
@router.callback_query(StateFilter("waiting_for_course_selection"))
async def process_course_selection(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if not data.startswith("select_course_"):
        await callback_query.message.answer("Неверный выбор. Попробуйте снова.")
        return
    course_id = int(data.replace("select_course_", ""))
    await state.update_data(course_id=course_id)
    await callback_query.message.answer("Введите название нового урока:")
    await state.set_state("waiting_for_lesson_title")
    await callback_query.answer()
@router.message(StateFilter("waiting_for_course_selection"))
async def process_course_selection(message: types.Message, state: FSMContext):
    course = await get_course_by_id(message.text)  # Ensure course title matches exactly
    if not course:
        await message.answer("Курс не найден. Попробуйте снова.")
        return
    await state.update_data(course_id=course.id)
    await message.answer("Введите название нового урока:")
    await state.set_state("waiting_for_lesson_title")
@router.message(StateFilter("waiting_for_lesson_title"))
async def process_lesson_title(message: types.Message, state: FSMContext):
    lesson_title = message.text
    await state.update_data(lesson_title=lesson_title)  # Сохраняем название урока в состоянии
    await message.answer("Введите описание для урока:")
    await state.set_state("waiting_for_lesson_description")
@router.message(StateFilter("waiting_for_lesson_description"))
async def process_lesson_description(message: types.Message, state: FSMContext):
    lesson_description = message.text
    data = await state.get_data()
    lesson_title = data.get("lesson_title")
    course_id = data.get("course_id")
    if not course_id:
        await message.answer("Ошибка: ID курса не найден. Сначала создайте курс с помощью команды /add_course.")
        return
    await add_lesson(course_id=course_id, title=lesson_title, description=lesson_description)
    await message.answer(f"Урок '{lesson_title}' добавлен в курс.")
    await state.clear()
@router.message(StateFilter("waiting_for_course_description"))
async def process_course_description(message: types.Message, state: FSMContext):
    course_description = message.text
    data = await state.get_data()
    course_title = data.get("course_title")
    course_id = await add_course(title=course_title, description=course_description)
    await state.update_data(course_id=course_id)

    await message.answer(f"Курс '{course_title}' (ID: {course_id}) добавлен! Теперь вы можете добавлять уроки.")
    await state.clear()






# Пример локализации сообщений
MESSAGES = {
    "main_menu": {
        "welcome": "Добро пожаловать! Выберите действие:",
    },
    "personal_info": {
        "welcome": "Вы в личном кабинете! Выберите действие:",
        "no_purchases": "У вас пока нет приобретённых курсов.",
        "purchases_list": "Ваши приобретённые курсы:",
        "no_progress": "Прогресс по этому курсу отсутствует.",
        "settings": "Настройки личного кабинета:"
    }
}
