from aiogram import Router, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton,ContentType, InlineKeyboardButton, InlineKeyboardMarkup,CallbackQuery
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database import get_visible_partners, add_partner,get_admins,get_user_language,load_texts,get_all_products,get_products_by_partner
from math import ceil
router = Router()
texts = load_texts('texts.xlsx')
class PartnerStates(StatesGroup):
    waiting_partner_info = State()
    waiting_partner_logo = State()
    confirm_partner_data = State()
    confirm_partner_visibility = State()

visibility_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
    ],
    resize_keyboard=True
)
ITEMS_PER_PAGE = 5
@router.message(lambda message: message.text and message.text.strip() in {str(texts['partners_button'].get(lang, '') or '').strip() for lang in texts['partners_button']})
async def partners_menu(message: Message):
    user_language = await get_user_language(message.from_user.id)
    buttons = [
        [KeyboardButton(text=texts['partners_info_button'][user_language])],
        [KeyboardButton(text=texts['become_partner'][user_language])],
        [KeyboardButton(text=texts['back_to_main_menu_button'][user_language])],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.message(lambda message: message.text and message.text.strip() in {str(texts['partners_info_button'].get(lang, '') or '').strip() for lang in texts['partners_info_button']})
async def partner_info(message: Message):
    partners = get_visible_partners()
    user_language = await get_user_language(message.from_user.id)
    if not partners:
        await message.answer(texts['list_partners_promt'].get(user_language, texts['list_partners_promt']['en']))
        return

    for name, credo, photo_id, status, partner_id in partners:  # Добавляем partner_id
        if user_language == "ru":
            text = (
                f"🔹 <b>{name}</b>\n"
                f"<i>Кредо:</i> {credo}\n"
                f"<i>Статус:</i> {status.capitalize()}"  # Отображаем статус партнёра
            )
            button_text = "Показать продукты"  # Кнопка для показа продуктов
        else:
            text = (
                f"🔹 <b>{name}</b>\n"
                f"<i>Credo:</i> {credo}\n"
                f"<i>Status:</i> {status.capitalize()}"  # Отображаем статус партнёра на английском
            )
            button_text = "Show Products"  # Кнопка для показа продуктов на английском

        # Инлайновая кнопка для отображения продуктов партнёра
        inline_button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"show_products_{partner_id}"  # Отправляем partner_id в callback_data
        )

        # Отправляем фото партнёра с текстом и кнопкой
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_button]])

        await message.answer_photo(
            photo=photo_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


@router.callback_query(lambda callback_query: callback_query.data.startswith("show_products_"))
async def show_partner_products(callback_query: CallbackQuery):

    partner_id = int(callback_query.data.split("_")[2])  # Извлекаем partner_id из callback_data
    user_language = await get_user_language(callback_query.from_user.id)
    # Получаем продукты партнёра
    products = get_products_by_partner(partner_id)

    if not products:
        if user_language == "ru":
            await callback_query.answer("У этого партнёра нет продуктов.")
            return
    else :
        await callback_query.answer("This partner has no products.")
        return


    # Отправляем список продуктов партнёра
    await send_product_page(message=callback_query.message, chat_id=callback_query.from_user.id, page=1,
                            user_language=await get_user_language(callback_query.from_user.id), partner_id=partner_id)

    # Ответ на клик по кнопке, чтобы не оставался индикатор загрузки
    await callback_query.answer()


async def send_product_page(message: Message, chat_id, page: int, user_language: str, product_type: str = None, partner_id: int = None):
    products = get_all_products()

    # Вывод всех продуктов, загруженных из базы данных

    # Если передан partner_id, фильтруем продукты по партнёру
    if partner_id:
        products = [p for p in products if p.get("partner_id") == partner_id]

    # Вывод продуктов после фильтрации по партнёру

    visible_products = [
        p for p in products
        if not p.get("is_hidden", False) and p.get("status") == "approved"
    ]

    # Вывод продуктов после фильтрации по статусу и скрытым продуктам

    if product_type:
        visible_products = [
            p for p in visible_products
            if product_type.lower() in p.get("product_type", "").lower()
        ]

        # Вывод продуктов после фильтрации по типу

    if not visible_products:
        await message.bot.send_message(chat_id, f"Нет доступных продуктов для типа: {product_type or 'всех'}")
        return

    total_pages = ceil(len(visible_products) / ITEMS_PER_PAGE)
    if not isinstance(page, int):
        page = 1
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    products_to_show = visible_products[start_index:end_index]

    # Вывод продуктов, которые будут отображаться на текущей странице

    text = "📋 Список продуктов:\n\n"
    for product in products_to_show:
        name = product["name"] if not product.get("is_personal") else "Продукт доступен по коду"
        text += f"🔹 {name} — {product['price']} VED\n"

    keyboard_buttons = []
    row = []
    for product in products_to_show:
        button_text = f"ℹ {product['name']} - {product['price']} VED"
        callback_data = f"product_info_{product['id']}"
        row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []

    if row:
        keyboard_buttons.append(row)
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page - 1}"))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"page_{page + 1}"))

    if navigation_buttons:
        keyboard_buttons.append(navigation_buttons)

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.bot.send_message(chat_id, text, reply_markup=keyboard)



@router.message(lambda message: message.text and message.text.strip() in {str(texts['become_partner'].get(lang, '') or '').strip() for lang in texts['become_partner']})
async def become_partner(message: Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    await state.update_data(user_language=user_language)
    await message.answer(texts['partner_ask'].get(user_language, texts['partner_ask']['en']))
    await state.set_state(PartnerStates.waiting_partner_info)

@router.message(StateFilter(PartnerStates.waiting_partner_info))
async def process_partner_info(message: Message, state: FSMContext):
    data = message.text.split("\n")
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)
    if len(data) < 2:
        await message.answer(texts['partner_become_error'].get(user_language, texts['partner_become_error']['en']))
        return

    name = data[0].strip()
    credo = data[1].strip()

    await state.update_data(name=name, credo=credo)
    await message.answer(texts['partner_logo_ava'].get(user_language, texts['partner_logo_ava']['en']))
    await state.set_state(PartnerStates.waiting_partner_logo)

@router.message(StateFilter(PartnerStates.waiting_partner_logo), F.content_type == ContentType.PHOTO)
async def process_partner_logo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id  # Получаем file_id изображения
    await state.update_data(photo_id=photo_id)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)

    # Спрашиваем пользователя, показывать его в списке или нет
    await message.answer(
        texts['ask_hide'].get(user_language, texts['ask_hide']['en']),
        reply_markup=visibility_keyboard
    )
    await state.set_state(PartnerStates.confirm_partner_visibility)

@router.message(StateFilter(PartnerStates.waiting_partner_logo))
async def wrong_logo_format(message: Message,state : FSMContext):
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await message.answer(texts['partner_no_img'].get(user_language, texts['partner_no_img']['en']))

@router.message(StateFilter(PartnerStates.confirm_partner_visibility), lambda message: message.text in ["Да", "Нет","Yes","No"])
async def process_visibility_choice(message: Message, state: FSMContext):
    show_in_list = True if message.text == "Да" or "Yes" else False
    # Получаем все данные
    data = await state.get_data()
    name = data.get('name')
    credo = data.get('credo')
    photo_id = data.get('photo_id')

    # Получаем ID пользователя, который стал партнёром
    partner_id = message.from_user.id

    # Добавляем партнёра с параметром видимости и partner_id
    add_partner(name, credo, photo_id, show_in_list, partner_id)

    # Уведомление админу
    admin_message = (
        f"🔔 Новая заявка на партнёрство:\n"
        f"👤 Имя партнёра: {name}\n"
        f"💬 Кредо: {credo}\n"
        f"🆔 ID пользователя: {partner_id}\n"
        f"👁️ Видимость в списке: {'Да' if show_in_list else 'Нет'}"
    )

    # Получаем список администраторов и отправляем уведомления
    admins = get_admins()
    for admin_id in admins:
        try:
            await message.bot.send_message(chat_id=admin_id, text=admin_message)
        except Exception as e:
            print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")

    # Очищаем состояние
    await state.clear()

    await message.answer(
        "Ваши данные успешно добавлены в список партнёров!",
        reply_markup=types.ReplyKeyboardRemove()
    )
@router.message(StateFilter(PartnerStates.confirm_partner_visibility))
async def wrong_visibility_format(message: Message):
    await message.answer("Пожалуйста, выберите 'Да' или 'Нет', используя кнопки ниже.")
