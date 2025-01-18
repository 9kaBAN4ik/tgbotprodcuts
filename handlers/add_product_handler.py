from aiogram import Router, types, F
from io import BytesIO
import time
import base64
import aiohttp
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton, InputFile,ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from database import ( get_user_role, add_product_to_db, get_all_products, get_product_by_code, get_product_by_id,
    get_user_balance, update_user_balance, add_product_to_user,get_all_courses, get_course_by_code, get_course_by_id,
    add_course, add_lesson, add_question,get_all_tags,add_user_subscription,get_all_product_types,get_popular_product_types,get_admins,load_texts,
                       get_referral_system_id,connect_db,get_referral_reward,add_referral_reward,get_user_language)
from aiogram.filters.state import StateFilter
from messages import *
from math import ceil
from handlers.menu_handler import back_to_main_menu
router = Router()

import logging

# Настройка логирования для детального отслеживания
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Состояния для добавления продукта
class AddProductForm(StatesGroup):
    name = State()  # Название продукта
    description = State()  # Описание продукта
    price = State()# Цена продукта
    image = State()
    category = State()
    is_subscription = State()  # Признак подписки
    subscription_period = State()  # Период подписки
    is_hidden = State()  # Добавьте это состояние
    search_product_by_code = State()
    after_purchase = State()  # Новое состояние
    is_educational_module = State()
    tags = State()  # Теги продукта
    product_type = State()
class QuestionStates(StatesGroup):
    waiting_for_options = State()  # Ожидаем варианты ответов
    waiting_for_correct_answer = State()

ITEMS_PER_PAGE = 5  # Количество продуктов на одной странице
# Загружаем текстовые данные
texts = load_texts('texts.xlsx')


@router.message(lambda message: message.text and message.text.strip() in {str(texts['products_button'].get(lang, '') or '').strip() for lang in texts['products_button']})
async def products(message: Message, state: FSMContext):
    logging.debug(f"Полученное сообщение: '{message.text}'")
    user_id = message.from_user.id
    user_language = await get_user_language(message.from_user.id)

    # Логируем начало обработки сообщения
    logging.debug(f"Обработчик 'products' был вызван. Полученный текст сообщения: '{message.text.strip()}'")

    # Логируем полученный текст сообщения и ожидаемый текст
    logging.debug(f"Ожидаемый текст кнопки 'Продукты': '{texts['products_button'][user_language].strip()}'")

    if message.text.strip().lower() == texts['products_button'][user_language].strip().lower():
        logger.debug(f"ID пользователя: {user_id}, Язык: {user_language}")
        user_role = await get_user_role(user_id)
        logging.debug(f"Язык пользователя: {user_language}")
        logging.debug(f"Текст совпал. Генерируем кнопки.")

        buttons = [
            [KeyboardButton(text=texts['buy_product_button'][user_language]),
             KeyboardButton(text=texts['subscribe_tag_button'][user_language])]
        ]

        if user_role in ['partner', 'admin']:
            logging.debug(f"Роль пользователя позволяет добавить продукт. Добавляем кнопку 'Добавить продукт'.")
            buttons.append([KeyboardButton(text=texts['add_product_button'][user_language])])

        buttons.append([KeyboardButton(text=texts['back_to_main_menu_button'][user_language])])

        # Клавиатура для продуктов
        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

        logging.debug(f"Отправляем сообщение с клавиатурой: {buttons}")
        await message.answer(
            texts['product_menu_prompt'].get(user_language, texts['product_menu_prompt']['en']),
            reply_markup=keyboard
        )
    else:
        # Логируем ошибку, если текст не совпал
        logging.error(f"Ошибка: Текст сообщения не совпал с ожидаемым.")
        logging.debug(
            f"Текст сообщения: '{message.text.strip()}', Ожидаемый текст: '{texts['products_button'][user_language].strip()}'")


# Обработка покупки продуктов (при нажатии на кнопку "Купить продукт")
@router.message(lambda message: message.text and message.text.strip() in {str(texts['buy_product_button'].get(lang, '') or '').strip() for lang in texts['buy_product_button']})
async def buy_product(message: Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    await send_product_page(message.chat.id, 1, user_language=user_language)  # Передаем язык явно


async def send_product_page(chat_id, page: int, user_language: str, product_type: str = None):
    products = get_all_products()
    from bot import bot
    visible_products = [
        p for p in products
        if not p.get("is_hidden", False) and p.get("status") == "approved"
    ]

    if product_type:
        visible_products = [
            p for p in visible_products
            if product_type.lower() in p.get("product_type", "").lower()
        ]

    if not visible_products:
        await bot.send_message(
            chat_id,
            texts.get(user_language, texts['en'])["no_products"].format(
                product_type=product_type or ('all' if user_language == 'en' else 'всех'))
        )
        return

    total_pages = ceil(len(visible_products) / ITEMS_PER_PAGE)
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    products_to_show = visible_products[start_index:end_index]
    text = texts['product_list'].get(user_language, texts['product_list']['en']) + "\n\n"

    for product in products_to_show:
        name = product["name"] if not product.get("is_personal") else texts['personal_product'].get(user_language,
                                                                                                    texts[
                                                                                                        'personal_product'][
                                                                                                        'en'])
        text += f"🔹 {name} — {product['price']} VED\n"

    keyboard_buttons = []
    row = []
    for product in products_to_show:
        button_text = f"ℹ {product['name']} - {product['price']} VED"
        callback_data = f"product_info_{product['id']}_{user_language}"
        row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []

    if row:
        keyboard_buttons.append(row)

    # Создание кнопки с языком
    keyboard_buttons.append([InlineKeyboardButton(
        text=texts['filters'].get(user_language, texts['filters']['en']),
        callback_data=f"show_filters_lang_{user_language}")
    ])
    if product_type:
        keyboard_buttons.append([InlineKeyboardButton(
            text=texts['reset_filter'].get(user_language, texts['reset_filter']['en']),
            callback_data=f"reset_filter_lang{user_language}"  # Используйте f-строку  # Измените на "reset_filter_lang", чтобы совпало с обработчиком
        )])
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(text=texts['previous'].get(user_language, texts['previous']['en']), callback_data=f"page_{page - 1}"))
    if page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton(text=texts['next'].get(user_language, texts['next']['en']), callback_data=f"page_{page + 1}"))

    if navigation_buttons:
        keyboard_buttons.append(navigation_buttons)

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await bot.send_message(chat_id, text, reply_markup=keyboard)


# Обработчик кнопки "Фильтры"
@router.callback_query(lambda cb: cb.data.startswith("show_filters_lang_"))
async def show_filters(callback_query: CallbackQuery):
    popular_types = get_popular_product_types()
    from bot import bot
    if not popular_types:
        await callback_query.answer("Нет достуpпных фильтров.")
        return
    user_language = callback_query.data.split('_')[-1]
    print(user_language)
    # Генерируем кнопки для популярных типов продуктов
    keyboard_buttons = [
        [InlineKeyboardButton(text=f"{type['type']} ({type['product_count']})",
                              callback_data=f"filter_type_{type['type']}")]
        for type in popular_types
    ]

    # Добавляем кнопку "Сбросить фильтр"
    keyboard_buttons.append([InlineKeyboardButton(text=texts['reset_filter'].get(user_language, texts['reset_filter']['en']), callback_data=f"reset_filter_lang{user_language}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await bot.send_message(callback_query.message.chat.id, "Выберите тип продукта:", reply_markup=keyboard)


# Обработчик сброса фильтра
@router.callback_query(lambda cb: cb.data.startswith("reset_filter_lang"))
async def reset_filter(callback_query: CallbackQuery):
    # Извлекаем язык из callback_data
    user_language = callback_query.data.split('lang')[1]
    await callback_query.answer("Фильтр отключён.")

    # Логируем перед вызовом send_product_page
    print(f"Sending product page for chat_id={callback_query.message.chat.id}, user_language={user_language}")

    await send_product_page(callback_query.message.chat.id, 1, user_language)


# Обработчик фильтрации по типу продукта
@router.callback_query(lambda cb: cb.data.startswith("filter_type_"))
async def filter_by_type(callback_query: CallbackQuery):
    product_type = callback_query.data.split("filter_type_")[1]
    await send_product_page(callback_query.message.chat.id, 1, product_type)


@router.message(lambda message: message.text == "⬅️ Previous" or message.text == "➡️ Next")
async def paginate_products(message: Message, state: FSMContext):
    # Получаем текущую страницу и обрабатываем переход
    user_data = await state.get_data()
    current_page = user_data.get("current_page", 1)

    if message.text == "⬅️ Previous":
        current_page -= 1
    elif message.text == "➡️ Next":
        current_page += 1

    await state.update_data(current_page=current_page)

    # Отправляем новую страницу продуктов
    await send_product_page(message.chat.id, current_page)


@router.callback_query(lambda callback: callback.data == "search_product_by_code")
async def search_product_by_code_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код продукта для поиска.")  # Запрашиваем код продукта
    await state.set_state("search_product_by_code")  # Устанавливаем состояние, чтобы ожидать код
    await callback.answer()  # Ответ на инлайн кнопку


@router.message(StateFilter("search_product_by_code"))
async def search_product_by_code_input(message: Message, state: FSMContext):
    product_code = message.text.strip()  # Получаем введённый код

    # Получаем продукт по коду из базы данных
    product = get_product_by_code(product_code)
    if product:
        # Сопоставление для категории
        category_mapping = {
            "session": "Онлайн-Сессия с терапевтом",
            "retreat": "Корпоративный ретрит"
        }
        category_text = category_mapping.get(product["category"], product["category"])

        # Статус подписки и период подписки
        if product["is_subscription"]:
            subscription_text = f"Подписка на {product['subscription_period']} дней"
        else:
            subscription_text = "Не подписка"

        # Формируем текст с информацией о продукте
        text = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: {product['price']} VED\n"
            f"📋 Категория: {category_text}\n"
            f"🔖 Статус: {subscription_text}"
        )

        # Отправляем изображение, если оно есть
        if product.get("image"):
            await message.answer_photo(photo=product["image"], caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(f"❌ Продукт с кодом <b>{product_code}</b> не найден.", parse_mode="HTML")

    await state.clear()  # Завершаем состояние после обработки

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
@router.message(lambda message: message.text == "Отмена")
async def cancel_process(message: Message, state: FSMContext):
    await state.clear()  # Сбрасываем состояние
    await message.answer("❌ Процесс отменён.", reply_markup=ReplyKeyboardRemove())

    # Вызываем функцию возвращения в главное меню
    await back_to_main_menu(message, state)

@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_product_button'].get(lang, '') or '').strip() for lang in texts['add_product_button']})
async def add_product(message: Message, state: FSMContext):
    user_id = message.from_user.id
    partner_id = message.from_user.id
    user_language = await get_user_language(message.from_user.id)
    user_role = await get_user_role(user_id)

    if user_role != 'partner' and user_role != 'admin':
        await message.answer("❌ У вас нет прав для добавления продуктов.")
        return
    await state.update_data(user_language=user_language)
    await message.answer(
    texts['new_product_promt'].get(user_language, texts['new_product_promt']['en']),
        reply_markup=cancel_keyboard()  # Клавиатура с кнопкой "Отмена"
    )
    await state.set_state(AddProductForm.name)
    await state.update_data(partner_id=partner_id)

@router.message(AddProductForm.name)
async def add_product_name(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    # Извлекаем user_language из состояния
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    await state.update_data(product_name=message.text)
    await message.answer(
        texts['new_product_desc_promt'].get(user_language, texts['new_product_desc_promt']['en']),
        reply_markup=cancel_keyboard()  # Клавиатура с кнопкой "Отмена"
    )
    await state.set_state(AddProductForm.description)


@router.message(AddProductForm.description)
async def add_product_description(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    await state.update_data(product_description=message.text)  # Сохраняем описание продукта
    await message.answer(
    texts['type_product_promt'].get(user_language, texts['type_product_promt']['en']),
        reply_markup=cancel_keyboard()  # Клавиатура с кнопкой "Отмена"
    )
    await state.set_state(AddProductForm.product_type)


# Логика добавления типа продукта
@router.message(AddProductForm.product_type)
async def add_product_type(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    await state.update_data(product_type=message.text)

    # Добавляем выбор категории
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Корпоративный ретрит", callback_data="category_retreat")],
            [InlineKeyboardButton(text="Онлайн-сессия с терапевтом", callback_data="category_session")],
        ]
    )

    # Кнопка "Отмена"
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(texts['select_product_type_promt'].get(user_language, texts['select_product_type_promt']['en']), reply_markup=keyboard)
    await message.answer(texts['cancel_promt'].get(user_language, texts['cancel_promt']['en']), reply_markup=cancel_keyboard)
    await state.set_state(AddProductForm.category)

# Логика добавления категории продукта
@router.callback_query(lambda callback: callback.data.startswith("category_"))
async def add_product_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]  # Извлекаем категорию
    await state.update_data(category=category)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    # Кнопка "Отмена"
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(texts['product_price_promt'].get(user_language, texts['product_price_promt']['en']), reply_markup=cancel_keyboard)
    await state.set_state(AddProductForm.price)


# Логика добавления цены продукта
@router.message(AddProductForm.price)
async def add_product_price(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    try:
        price = float(message.text)
        await state.update_data(price=price)

        # Кнопка "Отмена"
        cancel_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        # Запрашиваем изображение
        await message.answer(texts['send_product_image'].get(user_language, texts['send_product_image']['en']), reply_markup=cancel_keyboard)
        await state.set_state(AddProductForm.image)

    except ValueError:
        await message.answer("Цена должна быть числом. Попробуйте снова.")


# Логика добавления изображения
@router.message(AddProductForm.image)
async def add_product_image(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    if not message.photo:  # Проверяем, содержит ли сообщение фотографию
        await message.answer(texts['send_photo_again'].get(user_language, texts['send_photo_again']['en']))
        return

    # Сохраняем фотографию
    photo = message.photo[-1]  # Берем фотографию наибольшего размера
    file_id = photo.file_id
    await state.update_data(image=file_id)

    # Новый вопрос: "Что пользователь должен получить после покупки?"
    await message.answer(texts['after_purchase'].get(user_language, texts['after_purchase']['en']))
    await state.set_state(AddProductForm.after_purchase)
# Логика добавления тегов
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


# Логика добавления информации о том, что пользователь должен получить после покупки
@router.message(AddProductForm.after_purchase)
async def add_after_purchase_info(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    await state.update_data(after_purchase=message.text)  # Сохраняем данные
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    # Кнопка "Отмена"
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    # Новый этап для добавления тегов
    await message.answer(texts['after_purchase'].get(user_language, texts['after_purchase']['en']), reply_markup=cancel_keyboard)
    await state.set_state(AddProductForm.tags)


# Логика добавления тегов
@router.message(AddProductForm.tags)
async def add_product_tags(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    tags = message.text.split(",")  # Разделяем теги по запятой
    tags = [tag.strip() for tag in tags if tag.strip()]  # Убираем пробелы и пустые теги

    # Сохраняем теги в состоянии
    await state.update_data(tags=tags)

    # Логируем полученные теги
    print(f"Теги для продукта: {tags}")
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    # Переходим к следующему этапу (например, вопрос о подписке)
    await message.answer(texts['a_subscription'].get(user_language, texts['a_subscription']['en']))
    await state.set_state(AddProductForm.is_subscription)


# Логика выбора подписки (является ли продукт подпиской)
@router.message(AddProductForm.is_subscription)
async def add_is_subscription(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    is_subscription = message.text.strip().lower()

    if is_subscription == "да" or is_subscription == "yes":
        await state.update_data(is_subscription=True)
        await message.answer("Введите период подписки в днях:")
        await state.set_state(AddProductForm.subscription_period)
    elif is_subscription == "нет" or is_subscription == "no":
        await state.update_data(is_subscription=False)
        await ask_hide_product(message, state)
    else:
        await message.answer(texts['yes_no_product'].get(user_language, texts['yes_no_product']['en']))


# Логика ввода периода подписки
@router.message(AddProductForm.subscription_period)
async def add_subscription_period(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    try:
        subscription_period = int(message.text.strip())  # Преобразуем в число
        if subscription_period <= 0:
            await message.answer(texts['period_promt'].get(user_language, texts['period_promt']['en']))
            return
        await state.update_data(subscription_period=subscription_period)
        if user_language == "ru" :
            await message.answer(f"Период подписки установлен на {subscription_period} дней.")
        else :
            await message.answer(f"The subscription period is set to {subscription_period} days.")

        # Перенаправление к следующему шагу (например, скрытие продукта)
        await ask_hide_product(message, state)  # Или другой шаг, если необходимо

    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для периода подписки.")


# Вопрос о скрытии продукта
async def ask_hide_product(message: Message, state: FSMContext):
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Скрыть", callback_data="hide_product_yes")],
            [InlineKeyboardButton(text="Оставить видимым", callback_data="hide_product_no")],
        ]
    )

    # Кнопка "Отмена"
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer("Вы хотите скрыть продукт?", reply_markup=keyboard)
    await message.answer("Если хотите отменить процесс, нажмите 'Отмена'.", reply_markup=cancel_keyboard)
    await state.set_state(AddProductForm.is_hidden)


# Вопрос об образовательном модуле после видимости продукта
@router.callback_query(lambda callback: callback.data.startswith("hide_product_"))
async def set_product_visibility(callback: CallbackQuery, state: FSMContext):
    if callback.data == "hide_product_yes":
        is_hidden = True
    else:
        is_hidden = False

    await state.update_data(is_hidden=is_hidden)

    # Кнопка "Отмена"
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    # Спрашиваем, является ли продукт образовательным
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="educational_yes")],
            [InlineKeyboardButton(text="Нет", callback_data="educational_no")]
        ]
    )
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    await callback.message.answer(texts['hide_product_ask'].get(user_language, texts['hide_product_ask']['en']), reply_markup=keyboard)
    await callback.message.answer("Если хотите отменить процесс, нажмите 'Отмена'.", reply_markup=cancel_keyboard)
    await state.set_state(AddProductForm.is_educational_module)
    await callback.answer()


# Обработчик ответа об образовательном модуле
@router.callback_query(lambda callback: callback.data in ["educational_yes", "educational_no"])
async def process_educational_module(callback: CallbackQuery, state: FSMContext):
    if callback.data == "Отмена":
        await cancel_process(callback.message, state)
        return

    is_educational = callback.data == "educational_yes"
    await state.update_data(is_educational_module=is_educational)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    if is_educational:
        await callback.message.answer(texts['name_course'].get(user_language, texts['name_course']['en']))
        await state.set_state("waiting_for_course_title")
    else:
        await save_product(callback.message, state)
        await callback.message.answer(texts['product_normal_added'].get(user_language, texts['product_normal_added']['en']))
    await callback.answer()


@router.message(StateFilter("waiting_for_course_title"))
async def process_course_title(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    await state.update_data(course_title=message.text)  # Сохраняем название курса
    await message.answer(texts['course_promt'].get(user_language, texts['course_promt']['en']))
    await state.set_state("waiting_for_course_description")


@router.message(StateFilter("waiting_for_course_description"))
async def process_course_description(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    await state.update_data(course_description=message.text)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    data = await state.get_data()
    course_title = data.get("course_title")
    course_description = data.get("course_description")

    # Добавляем курс и получаем его ID
    course_id = await add_course(
        name=course_title,
        description=course_description,
        partner_id=message.from_user.id
    )

    # Сохраняем course_id в состояние для дальнейшего использования
    await state.update_data(course_id=course_id)

    print(f"Created course with ID: {course_id}")
    if user_language == "ru":
        await message.answer(f"Курс '{course_title}' добавлен.\nТеперь добавляем урок, введите название урока.")
    else:
        await message.answer(f"Курс '{course_title}' добавлен.\nNow add a lesson, enter the title of the lesson.")
    await state.set_state("waiting_for_lesson_title")


@router.message(StateFilter("waiting_for_lesson_title"))
async def process_lesson_title(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    await state.update_data(lesson_title=message.text)  # Сохраняем название урока
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    await message.answer(texts['lesson_desc_promt'].get(user_language, texts['lesson_desc_promt']['en']))
    await state.set_state("waiting_for_lesson_description")


@router.message(StateFilter("waiting_for_lesson_description"))
async def process_lesson_description(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    await state.update_data(lesson_description=message.text)

    data = await state.get_data()
    lesson_title = data.get("lesson_title")
    lesson_description = data.get("lesson_description")
    course_id = data.get("course_id")
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    if not course_id:
        await message.answer(texts['no_course_id'].get(user_language, texts['no_course_id']['en']))
        return

    lesson_id = await add_lesson(
        course_id=course_id,
        title=lesson_title,
        description=lesson_description
    )

    # Сохраняем lesson_id в состояние для дальнейшего использования
    await state.update_data(lesson_id=lesson_id)

    print(f"Добавлен урок с ID: {lesson_id}")  # Логирование ID урока
    if user_language == "ru":
        await message.answer(f"Урок '{lesson_title}' добавлен.\nТеперь добавьте вопросы к уроку.")
    else:
        await message.answer(f"Lesson '{lesson_title}' has been added.\nNow add questions to the lesson.")
    await state.set_state("waiting_for_question_text")


@router.message(StateFilter("waiting_for_question_text"))
async def process_question_text(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    question_text = message.text
    await state.update_data(question_text=question_text)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    await message.answer(texts['questions_in_products'].get(user_language, texts['questions_in_products']['en']))
    await state.set_state(QuestionStates.waiting_for_options)


@router.message(QuestionStates.waiting_for_options)
async def process_question_options(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    options = message.text.split(",")
    options = [option.strip() for option in options if option.strip()]
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    if len(options) > 3:
        if user_language == "ru":
            await message.answer("Не более трех вариантов ответа. Попробуйте снова.")
        else:
            await message.answer("Up to three possible answers. Try again.")
        return

    await state.update_data(question_options=options)

    await message.answer("Введите правильный вариант ответа (1, 2 или 3):")
    await state.set_state("waiting_for_correct_answer")


@router.message(StateFilter("waiting_for_correct_answer"))
async def process_correct_answer(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    correct_answer = message.text.strip()

    # Получаем данные из состояния
    data = await state.get_data()
    question_text = data.get("question_text")
    question_options = data.get("question_options")
    lesson_id = data.get("lesson_id")  # Получаем lesson_id из состояния

    print(f"lesson_id из состояния: {lesson_id}")  # Логирование для отладки

    if not lesson_id:
        if user_language == "ru" :
            await message.answer("Ошибка: урок не был выбран. Попробуйте снова.")
        else:
            await message.answer("Error: No lesson was selected. Try again.")
        return

    try:
        correct_answer_index = int(correct_answer) - 1
        if correct_answer_index < 0 or correct_answer_index >= len(question_options):
            if user_language == "ru":
                await message.answer("Неправильный номер варианта. Попробуйте снова.")
            else:
                await message.answer("Invalid variant number. Try again.")
            return
    except ValueError:
        await message.answer("Введите номер правильного варианта (1, 2 или 3).")
        return

    correct_answer_text = question_options[correct_answer_index]

    # Добавляем вопрос с lesson_id
    await add_question(
        lesson_id=lesson_id,  # Передаем lesson_id
        question_text=question_text,
        options=question_options,
        correct_answer=correct_answer_text
    )

    if user_language == "ru":
        await message.answer(
            "Вопрос добавлен! Хотите добавить ещё вопросы? Напишите 'да' для продолжения или 'нет' для завершения.")
    else:
        await message.answer(
            "Question added! Want to add more questions? Write 'yes' to continue or 'no' to finish.")
    await state.set_state("waiting_for_add_more_questions")


@router.message(StateFilter("waiting_for_add_more_questions"))
async def process_add_more_questions(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    answer = message.text.strip().lower()
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    if answer == "да" or answer == "yes":
        if user_language =="ru":
            await message.answer("Введите текст следующего вопроса:")
            await state.set_state("waiting_for_question_text")
        else:
            await message.answer("Enter the text of the next question:")
            await state.set_state("waiting_for_question_text")
    elif answer == "нет" or answer == "no":
        # Получаем имя и описание продукта из состояния
        data = await state.get_data()
        product_name = data.get("product_name")
        product_description = data.get("product_description")

        # Завершаем добавление вопросов и возвращаем на предыдущий этап
        await save_product(message, state, product_name, product_description)
        if user_language == "ru":
            await message.answer("Добавление вопросов завершено. Продукт успешно добавлен!")
        else:
            await message.answer("Adding questions completed. Product added successfully!")
    else:
        await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")


async def save_product(message: Message, state: FSMContext, name: str = None, description: str = None,course_id: int = None):
    # Получаем данные из состояния
    product_data = await state.get_data()

    name = product_data.get("product_name", name)  # Используем сохраненное название продукта
    description = product_data.get("product_description", description)  # Используем сохраненное описание продукта
    tags = product_data.get("tags", [])
    image = product_data.get("image")
    is_hidden = product_data.get("is_hidden", False)
    category = product_data.get("category")
    is_subscription = product_data.get("is_subscription", False)
    subscription_period = product_data.get("subscription_period")
    after_purchase = product_data.get("after_purchase")
    partner_id = product_data.get("partner_id")  # Получаем partner_id из состояния
    product_type = product_data.get("product_type")
    product_code = f"PRD-{int(time.time())}"

    # Проверка, является ли продукт образовательным
    is_educational = product_data.get("is_educational_module", False)

    if is_educational:
        # Логика для образовательного продукта
        course_name = product_data.get("course_title")
        course_description = product_data.get("course_description")

        # Добавление курса в базу данных, если это образовательный продукт
        if not course_id:
            course_id = await add_course(
                name=course_name,
                description=course_description,
                partner_id=message.from_user.id
            )

        # Получаем уроки и добавляем их
        lessons = product_data.get("lessons", [])
        for lesson_data in lessons:
            lesson_id = await add_lesson(
                course_id=course_id,
                lesson_name=lesson_data["lesson_name"],
                lesson_content=lesson_data["lesson_content"]
            )

            # Добавляем вопросы для каждого урока
            questions = lesson_data.get("questions", [])
            for question_data in questions:
                await add_question(
                    lesson_id=lesson_id,
                    question_text=question_data["question_text"],
                    correct_answer=question_data["correct_answer"],
                    answers=question_data["answers"]
                )

        # Добавляем сам продукт как образовательный
        await add_product_to_db(
            name=name,
            description=description,
            price=product_data["price"],
            product_type=product_type,
            is_subscription=is_subscription,
            partner_id=message.from_user.id,
            image=image,
            subscription_period=subscription_period,
            after_purchase=after_purchase,
            code=product_code,
            is_hidden=is_hidden,
            category=category,
            course_id=course_id,  # Передаем course_id для образовательного продукта
            tags=tags
        )

        await message.answer(
            f"Образовательный продукт '{name}' с курсом '{course_name}' успешно добавлен!"
            f"Продукт '{name}' успешно добавлен! Уникальный код продукта: {product_code}"
        )

    else:
        # Логика для обычного продукта
        await add_product_to_db(
            name=name,
            description=description,
            price=product_data["price"],
            is_subscription=is_subscription,
            partner_id=partner_id,
            product_type=product_type,
            image=image,
            subscription_period=subscription_period,
            after_purchase=after_purchase,
            code=product_code,
            category=category,
            is_hidden=is_hidden,
            course_id=course_id,  # Передаем course_id, если это образовательный продукт
            tags=tags
        )

        await message.answer(
            f"Продукт '{name}' успешно добавлен! Уникальный код продукта: {product_code}"
        )

    # Очищаем данные состояния после сохранения продукта
    await state.clear()


@router.callback_query(lambda callback: callback.data.startswith("product_info_"))
async def product_info_handler(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[2])  # Извлекаем ID продукта
        user_language = str(callback.data.split("_")[3])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Ошибка в данных продукта.")
        return

    # Получаем продукт и информацию о пользователе
    product = get_product_by_id(product_id)  # Предполагается, что функция возвращает словарь продукта
    user_id = callback.from_user.id
    user_balance = await get_user_balance(user_id)  # Обновлено: функция асинхронная

    if not product:
        await callback.message.answer("❌ Продукт не найден.")
        return

    # Проверяем, скрыт ли продукт
    if product.get("is_hidden"):
        await callback.message.answer("❌ Этот продукт скрыт.")
        return

    # Сопоставление категорий
    category_mapping = {
        "session": "Онлайн-Сессия с терапевтом",
        "retreat": "Корпоративный ретрит"
    }
    category_text = category_mapping.get(product["category"], product["category"])

    # Проверка подписки
    if product["is_subscription"]:
        subscription_text = f"Подписка на {product['subscription_period']} дней"
    else:
        subscription_text = "Не подписка"
    if user_language == "ru" :
        product_text = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: {product['price']} VED\n"
            f"📋 Категория: {category_text}\n"
            f"🔖 Статус: {subscription_text}\n"
            f"💳 Ваш баланс: {user_balance} VED"
        )
    else :
        product_text =(
        f"📦 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 Price: {product['price']} VED\n"
        f"📋 Category: {category_text}\n"
        f"🔖 Status: {subscription_text}\n"
        f"💳 Your Balance: {user_balance} VED"
        )
    # Создаем клавиатуру с кнопкой "Купить", если у пользователя хватает средств
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if user_balance >= product["price"]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=texts['buy_product_add'].get(user_language, texts['buy_product_add']['en']),
                callback_data=f"buy_product_{product_id}_{user_language}"
            )
        ])

    # Отправляем информацию о продукте
    try:
        if product.get("image"):
            await callback.message.answer_photo(
                photo=product["image"],
                caption=product_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                text=product_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        await callback.message.answer("❌ Не удалось отправить информацию о продукте.")
        print(f"Ошибка отправки сообщения: {e}")


@router.callback_query(lambda callback: callback.data.startswith("buy_product_"))
async def buy_product_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])  # Извлекаем ID продукта
    user_language = str(callback.data.split("_")[3])
    user_id = callback.from_user.id
    product = get_product_by_id(product_id)  # Получаем продукт по ID
    user_balance = await get_user_balance(user_id)  # Получаем баланс пользователя

    if product:
        if user_balance >= product["price"]:
            # Изменяем баланс пользователя
            new_balance = user_balance - product["price"]
            update_user_balance(user_id, new_balance)

            # Отладочное сообщение: проверим новый баланс перед отправкой
            print(f"Новый баланс пользователя {user_id}: {new_balance}")

            # Добавляем продукт пользователю
            add_product_to_user(user_id, product_id)

            # Уведомление пользователя о покупке
            if user_language =="ru":
                await callback.message.answer(
                    f"✅ Вы успешно купили <b>{product['name']}</b> за {product['price']} VED!\n"
                    f"💳 Ваш новый баланс: {new_balance} VED",
                    parse_mode="HTML"
                )
            else :
                await callback.message.answer(
                    f"✅ You successfully purchased <b>{product['name']}</b> for {product['price']} VED!\n"
                    f"💳 Your new balance: {new_balance} VED",
                    parse_mode="HTML"
                )


            # Награда для пригласившего пользователя (если он есть)
            # Получаем активную реферальную систему
            referral_system_id = get_referral_system_id()

            if referral_system_id:
                # Находим реферера для данного пользователя
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT referrer_id FROM referrals
                    WHERE referred_id = ?
                """, (user_id,))
                referrer = cursor.fetchone()
                conn.close()

                if referrer:
                    referrer_id = referrer[0]
                    # Определяем уровень реферала
                    level = 1  # Для упрощения примера мы берем уровень 1 (можно добавить логику для разных уровней)

                    # Получаем размер награды для уровня
                    reward_percentage = get_referral_reward(referral_system_id, level)

                    # Рассчитываем награду
                    reward_amount = (product["price"] * reward_percentage) / 100

                    # Добавляем награду пригласившему пользователю
                    if reward_amount > 0:
                        add_referral_reward(referrer_id, reward_amount)

                        # Уведомление для пригласившего пользователя
                        try:
                            if user_language == "ru":
                                await callback.bot.send_message(
                                    chat_id=referrer_id,
                                    text=f"🎉 Вы получили {reward_amount} VED за покупку, совершённую вашим рефералом!"
                                    )
                            else :
                                await callback.bot.send_message(
                                    chat_id=referrer_id,
                                    text=f"🎉 You received {reward_amount} VED for a purchase made by your referral!"
                                )
                        except Exception as e:
                            print(f"Не удалось отправить сообщение пригласившему пользователю {referrer_id}: {e}")

            # Уведомление администраторам
            admin_message = (
                f"🛒 Покупка продукта:\n"
                f"👤 Пользователь: {callback.from_user.full_name} (ID: {user_id})\n"
                f"📦 Продукт: {product['name']}\n"
                f"💰 Цена: {product['price']} VED"
            )
            admins = get_admins()
            for admin_id in admins:
                try:
                    await callback.bot.send_message(chat_id=admin_id, text=admin_message)
                except Exception as e:
                    print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")

            # Уведомление автору продукта
            partner_id = product.get("partner_id")  # Получаем ID автора продукта
            if partner_id:
                try:
                    author_message = (
                        f"🔔 Ваш продукт был куплен!\n"
                        f"📦 Продукт: {product['name']}\n"
                        f"👤 Покупатель: {callback.from_user.full_name} (ID: {user_id})\n"
                        f"💰 Сумма: {product['price']} VED"
                    )
                    await callback.bot.send_message(chat_id=partner_id, text=author_message)
                except Exception as e:
                    print(f"Не удалось отправить сообщение автору продукта {partner_id}: {e}")
        else:
            await callback.message.answer("❌ У вас недостаточно средств для покупки этого продукта.")
    else:
        await callback.message.answer("❌ Продукт не найден.")





@router.callback_query(lambda callback: callback.data.startswith("page_"))
async def pagination_handler(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])  # Извлекаем номер страницы
    await send_product_page(callback.message.chat.id, page)  # Отправляем новую страницу продуктов



# Обработчик кнопки "Купить Курс"
@router.message(lambda message: message.text == "Купить Курс")
async def buy_course(message: Message):
    await send_course_page(message.chat.id, 1)  # Начинаем с первой страницы

async def send_course_page(message,chat_id, page: int):
    courses = get_all_courses()  # Получаем список курсов
    visible_courses = [c for c in courses if not c.get("is_hidden", False)]  # Только видимые курсы

    total_pages = ceil(len(visible_courses) / ITEMS_PER_PAGE)
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    courses_to_show = visible_courses[start_index:end_index]

    text = "📚 Список курсов:\n\n"
    for course in courses_to_show:
        text += f"🔹 {course['name']} — {course['price']} VED\n"

    keyboard_buttons = []
    for course in courses_to_show:
        button_text = f"ℹ {course['name']} - {course['price']} VED"
        callback_data = f"course_info_{course['id']}"
        keyboard_buttons.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"course_page_{page-1}"))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"course_page_{page+1}"))

    keyboard_buttons.extend(navigation_buttons)
    keyboard_buttons.append(InlineKeyboardButton(text="🔍 Поиск по коду курса", callback_data="search_course_by_code"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[keyboard_buttons])

    await message.bot.send_message(chat_id, text, reply_markup=keyboard)

# Обработчик для получения информации о курсе при нажатии на кнопку
@router.callback_query(lambda callback: callback.data.startswith("course_info_"))
async def course_info_callback(callback: CallbackQuery):
    try:
        course_id = int(callback.data.split("_")[2])  # Извлекаем ID курса
    except (IndexError, ValueError):
        await callback.message.answer("❌ Ошибка в данных курса.")
        return

    # Получаем курс
    course = await get_course_by_id(course_id)  # Убедитесь, что функция корректно работает
    if not course:
        await callback.message.answer("❌ Курс не найден.")
        return

    # Проверяем скрытие курса
    if course.get("is_hidden"):
        await callback.message.answer("❌ Этот курс скрыт.")
        return

    # Формируем текст
    course_text = (
        f"📚 <b>{course['title']}</b>\n\n"
        f"{course['description']}\n\n"
        f"💰 Цена: {course.get('price', 'N/A')} VED"
    )

    # Отправляем сообщение
    try:
        if course.get("image"):
            await callback.message.answer_photo(
                photo=course["image"],
                caption=course_text,
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                text=course_text,
                parse_mode="HTML"
            )
    except Exception as e:
        await callback.message.answer("❌ Не удалось отправить информацию о курсе.")
        print(f"Ошибка отправки сообщения: {e}")

# Обработчик для навигации по страницам курсов
@router.callback_query(lambda callback: callback.data.startswith("course_page_"))
async def paginate_courses(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    await send_course_page(callback.message.chat.id, page)
    await callback.answer()  # Ответ на инлайн-кнопку

# Поиск курса по коду
@router.callback_query(lambda callback: callback.data == "search_course_by_code")
async def search_course_by_code_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код курса для поиска.")
    await state.set_state("search_course_by_code")
    await callback.answer()

@router.message(StateFilter("search_course_by_code"))
async def search_course_by_code_input(message: Message, state: FSMContext):
    course_code = message.text.strip()

    course = get_course_by_code(course_code)

    if course:
        text = (
            f"📚 <b>{course['name']}</b>\n\n"
            f"{course['description']}\n\n"
            f"💰 Цена: {course['price']} VED"
        )
        if course.get("image"):
            await message.answer_photo(course["image"], caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(f"❌ Курс с кодом {course_code} не найден.")

    await state.set_state(None)


# Обработчик для кнопки "Подписаться на тэг"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['subscribe_tag_button'].get(lang, '') or '').strip() for lang in texts['subscribe_tag_button']})
async def subscribe_to_tag(message: types.Message):
    tags = get_all_tags()
    user_language = await get_user_language(message.from_user.id)
    if not tags:
        if user_language == "ru":
            await message.answer("Тэги пока не добавлены.")
        else :
            await message.answer("Tags not added yet.")
        return

    # Создаем кнопки для всех тэгов
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tag, callback_data=f"subscribe_tag:{tag}")]
            for tag in tags
        ]
    )
    if user_language == "ru":
        await message.answer("Выберите тэг для подписки:", reply_markup=keyboard)
    else :
        await message.answer("Select a tag to subscribe to:", reply_markup=keyboard)


# Обработчик нажатия на кнопку тега
@router.callback_query(F.data.startswith("subscribe_tag:"))
async def process_tag_subscription(callback: CallbackQuery):
    tag = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user_language = await get_user_language(user_id)
    # Попытка добавить подписку пользователя на выбранный тэг
    success = add_user_subscription(user_id, tag)
    if success:
        if user_language == "ru" :
            await callback.answer(f"Вы успешно подписались на тэг '{tag}'!")
        else:
            await callback.answer(f"You have successfully subscribed to tag '{tag}'!")
    else:
        if user_language == "ru":
            await callback.answer(f"Вы уже подписаны на тэг '{tag}'.")
        else :
            await callback.answer(f"You are already subscribed to tag '{tag}'.")