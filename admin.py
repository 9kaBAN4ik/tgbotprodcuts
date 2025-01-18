# admin.py
import re
import sqlite3
from aiogram import Router, F, types
from aiogram.types import Message, ContentType,ReplyKeyboardRemove,InputFile,BufferedInputFile,InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID  # Главный администратор из config
from database import (set_user_role, get_user_role,get_user_courses, get_user_products,
                        add_aphorism,add_image,get_rate, update_rate,update_product_status,get_pending_products,
                      get_users_by_tag,get_all_tags,get_current_rewards,update_reward,get_all_products_two,
                      get_users_by_product,get_user_balance,get_all_products,get_product_by_id,get_partners_with_status,
                      get_partner_by_id_admin,update_partner_status,get_partner_by_id,get_feedbacks,update_user_role_for_partner,
                      get_user_by_id_admin,get_all_aphorisms,aphorism_exists,delete_aphorism,update_aphorism_text,update_aphorism_author,save_referral_system,
                      get_all_users,add_balance_to_user,connect_db,load_texts,get_user_language,get_current_referral_system,update_referral_rewards,create_referral_system)# Работа с ролями пользователей
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from math import ceil
import logging
import random
import os
router = Router()
ITEMS_PER_PAGE = 5
# Состояния для добавления афоризма
class AddAphorism(StatesGroup):
    waiting_for_text = State()
    waiting_for_author = State()
# Состояния для загрузки фото афоризма
class AphorismStates(StatesGroup):
    waiting_for_image = State()
# Определяем состояния для FSM
class AddPartnerState(StatesGroup):
    waiting_for_user_id = State()
class ProductMessageState(StatesGroup):
    waiting_for_message = State()
class ReferralEditState(StatesGroup):
    waiting_for_new_reward = State()
class AddAdminState(StatesGroup):
    waiting_for_user_id = State()
class RateUpdateState(StatesGroup):
    waiting_for_rate = State()
class BroadcastState(StatesGroup):
    waiting_for_message_admin = State()
class DeleteAphorism(StatesGroup):
    waiting_for_id = State()
class EditAphorism(StatesGroup):
    waiting_for_id = State()
    waiting_for_choice = State()
    waiting_for_new_text = State()
    waiting_for_new_author = State()
class AddBalanceStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()
class LotteryStates(StatesGroup):
    waiting_for_price = State()
class FileUpdateState(StatesGroup):
    waiting_for_file = State()

texts = load_texts('texts.xlsx')
FILE_PATH = 'texts.xlsx'
@router.message(lambda message: message.text and message.text.strip() in {str(texts['admin_panel_button'].get(lang, '') or '').strip() for lang in texts['admin_panel_button']})
async def admin_menu(message: Message):
    user_role = await get_user_role(message.from_user.id)
    user_id = message.from_user.id
    user_language = await get_user_language(user_id)
    # Приводим оба значения к целым числам для точного сравнения
    if user_role != 'admin':
        # Отправляем пользователя обратно в главное меню
        await message.answer(
            "У вас нет доступа к админ-панели.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[KeyboardButton(text=texts['back_to_main_menu_button'][user_language])],
                resize_keyboard=True
            )
        )
        return

    # Если пользователь админ, показываем админское меню
    buttons = [
        [KeyboardButton(text=texts["add_admin_button"][user_language]),
         KeyboardButton(text=texts["add_partner_button_admin"][user_language])],
        [KeyboardButton(text=texts["view_all_products"][user_language]),
         KeyboardButton(text=texts["show_pending_products"][user_language])],
        [KeyboardButton(text=texts["add_aforism"][user_language]),
         KeyboardButton(text=texts["add_aforism_photo"][user_language])],
        [KeyboardButton(text=texts["delete_aforism"][user_language]),
         KeyboardButton(text=texts["edit_aforism"][user_language])],
        [KeyboardButton(text=texts["view_query_results"][user_language]),
         KeyboardButton(text=texts["edit_referral_system"][user_language])],
        [KeyboardButton(text=texts["display_current_exchange_rate"][user_language]),
         KeyboardButton(text=texts["set_new_exchange_rate"][user_language])],
        [KeyboardButton(text=texts["send_product_broadcast"][user_language]),
         KeyboardButton(text=texts["send_tag_broadcast"][user_language])],
        [KeyboardButton(text=texts["view_partner_applications"][user_language]),
         KeyboardButton(text=texts["support_requests"][user_language])],
        [KeyboardButton(text=texts["view_all_users"][user_language]),
         KeyboardButton(text=texts["add_balance_to_user"][user_language])],
        [KeyboardButton(text=texts["start_lottery"][user_language]),
         KeyboardButton(text=texts["end_lottery"][user_language])],
        [KeyboardButton(text=texts["set_lottery_ticket_price"][user_language]),
         KeyboardButton(text=texts["view_lottery_participants"][user_language])],
        [KeyboardButton(text=str(texts['file_command'].get(user_language, "default"))),
         KeyboardButton(text=str(texts['new_file_command'].get(user_language, "default")))],
        [KeyboardButton(text=str(texts['create_referral_system'].get(user_language,"default")))],
        [KeyboardButton(text=texts["back_to_main_menu_button"][user_language])],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer("Выберите интересующий раздел:", reply_markup=keyboard)


async def is_admin(user_id: int) -> bool:
    """
    Проверяем, является ли пользователь администратором.
    """
    if user_id == int(ADMIN_ID):  # Главный администратор
        return True

    # Проверка роли в базе данных
    role = await get_user_role(user_id)
    return role == 'admin'


# Команда для добавления партнёра
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_partner_button_admin'].get(lang, '') or '').strip() for lang in texts['add_partner_button_admin']})
async def start_add_partner(message: Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    # Проверяем, является ли отправитель администратором
    if not await is_admin(message.from_user.id):
        await message.answer(texts['add_partner_admin_promt'].get(user_language, texts['add_partner_admin_promt']['en']))
        return
    await message.answer(texts['add_partner_send_id'].get(user_language, texts['add_partner_send_id']['en']))
    await state.set_state(AddPartnerState.waiting_for_user_id)


@router.message(AddPartnerState.waiting_for_user_id, F.text.isdigit())
async def process_partner_user_id(message: Message, state: FSMContext):
    user_id = int(message.text)
    user_language = await get_user_language(user_id)
    await state.update_data(user_language=user_language)
    # Устанавливаем роль пользователя как партнёр:
    if user_language == "ru":
        await message.answer(f"Пользователь с user_id {user_id} теперь партнёр!")
    else :
        await message.answer(f"User with user_id {user_id} is now a partner!")
    await state.clear()


@router.message(AddPartnerState.waiting_for_user_id)
async def invalid_partner_user_id(message: Message,state : FSMContext):
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    if user_language == "ru":
        await message.answer("Пожалуйста, введите корректный user_id (только цифры).")
    else :
        await message.answer("Please enter a valid user_id (numbers only).")


# Команда для добавления администратора
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_admin_button'].get(lang, '') or '').strip() for lang in texts['add_admin_button']})
async def start_add_admin(message: Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    # Проверяем, является ли отправитель администратором
    if not await is_admin(message.from_user.id):
        await message.answer(texts['add_partner_admin_promt'].get(user_language, texts['add_partner_admin_promt']['en']))
        return

    await message.answer(texts['add_admin_send_id'].get(user_language, texts['add_admin_send_id']['en']))
    await state.set_state(AddAdminState.waiting_for_user_id)


@router.message(AddAdminState.waiting_for_user_id, F.text.isdigit())
async def process_admin_user_id(message: Message, state: FSMContext):
    user_id = int(message.text)

    # Устанавливаем роль пользователя как администратор
    await set_user_role(user_id, 'admin')
    await message.answer(f"Пользователь с user_id {user_id} теперь администратор!")
    await state.clear()


@router.message(AddAdminState.waiting_for_user_id)
async def invalid_admin_user_id(message: Message):
    await message.answer("Пожалуйста, введите корректный user_id (только цифры).")

# Обработчик команды "Добавить афоризм"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_aforism'].get(lang, '') or '').strip() for lang in texts['add_aforism']})
async def cmd_add_aphorism(message: types.Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    await state.update_data(user_language=user_language)
    await message.answer(texts['add_aphorism_promt'].get(user_language, texts['add_aphorism_promt']['en']))
    await state.set_state(AddAphorism.waiting_for_text)

# Принимаем текст афоризма
@router.message(AddAphorism.waiting_for_text)
async def process_aphorism_text(message: types.Message, state: FSMContext):
    await state.update_data(aphorism_text=message.text)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)
    await message.answer(texts['add_aphorism_author'].get(user_language, texts['add_aphorism_author']['en']))
    await state.set_state(AddAphorism.waiting_for_author)

# Принимаем автора афоризма и сохраняем
@router.message(AddAphorism.waiting_for_author)
async def process_aphorism_author(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data['aphorism_text']
    author = message.text

    # Сохраняем афоризм в базу данных
    add_aphorism(text, author)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    if user_language == "ru":
        await message.answer("Афоризм был успешно добавлен!")
    else:
        await message.answer("Aphorism was added succesfully!")
    await state.clear()

# Обработчик для команды "Добавить фото афоризма"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_aforism_photo'].get(lang, '') or '').strip() for lang in texts['add_aforism_photo']})
async def cmd_add_image(message: types.Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)
    await state.set_state(AphorismStates.waiting_for_image)
    await message.answer(texts['aphorism_send_photo'].get(user_language, texts['aphorism_send_photo']['en']))
# Обработчик для сообщений с фото в состоянии waiting_for_image
@router.message(StateFilter(AphorismStates.waiting_for_image), F.content_type == ContentType.PHOTO)
async def process_image_upload(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id  # Получаем file_id изображения
    add_image(file_id)  # Добавляем в базу данных
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    if user_language == "ru":
        await message.answer("Изображение успешно добавлено и будет использоваться с афоризмами!")
        await state.clear()
    else :
        await message.answer("Image successfully added and will be used with aphorisms!")
        await state.clear()
    await state.clear()




# Создаем инлайн-клавиатуру с выбором валют
def get_currency_keyboard():
    buttons = [
        [InlineKeyboardButton(text="USDT", callback_data="update_rate:USDT")],
        [InlineKeyboardButton(text="BTC", callback_data="update_rate:BTC")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Хендлер для запроса выбора валюты
@router.message(lambda message: message.text and message.text.strip() in {str(texts['set_new_exchange_rate'].get(lang, '') or '').strip() for lang in texts['set_new_exchange_rate']})
async def ask_for_currency_selection(message: Message,state : FSMContext):
    user_language = await get_user_language(message.from_user.id)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)
    await message.answer(
        (texts['aphorism_send_photo'].get(user_language, texts['aphorism_send_photo']['en'])),
        reply_markup=get_currency_keyboard()
    )

# Хендлер для обработки нажатий на кнопки
@router.callback_query(F.data.startswith("update_rate:"))
async def handle_currency_selection(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)
    currency = callback.data.split(":")[1]  # Получаем выбранную валюту

    await state.update_data(currency=currency)  # Сохраняем валюту в состоянии
    if user_language == "ru":
        await callback.message.answer(
            f"🛠 Введите новый курс для **{currency}** в формате: `ЧИСЛО`\n\nПример: `1.15`"
        )
    else :
        await callback.message.answer(
            f"🛠 Enter new rate for **{currency}** in format: `NUMBER`\n\nExample: `1.15`"
        )
    await state.set_state(RateUpdateState.waiting_for_rate)  # Устанавливаем состояние ожидания ввода курса
    await callback.answer()  # Закрываем уведомление о нажатии кнопки

# Хендлер для ввода нового курса
@router.message(StateFilter(RateUpdateState.waiting_for_rate), F.text)
async def handle_rate_update(message: Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")
        data = await state.get_data()  # Получаем сохраненные данные
        currency = data.get("currency")  # Извлекаем выбранную валюту
        new_rate = float(message.text.strip())  # Конвертируем ввод в число

        # Обновляем курс валюты в базе данных
        update_rate(currency, new_rate)
        if user_language == "ru":
            await message.answer(f"✅ Курс **{currency}** успешно обновлён на **{new_rate}**.")
        else :
            await message.answer(f"✅ Rate **{currency}** successfully updated to **{new_rate}**.")
    except ValueError:
        if user_language == "ru":
            await message.answer("❌ Неправильный формат ввода. Введите число.\nПример: `1.15`")
        else :
            await message.answer("❌ Incorrect input format. Enter a number.\nExample: `1.15`")
    except Exception as e:
        if user_language == "ru" :
            await message.answer(f"❌ Произошла ошибка при обновлении курса: {e}")
        else :
            await message.answer(f"❌ An error occurred while updating the course: {e}")
    finally:
        await state.clear()  # Сбрасываем состояние

@router.message(lambda message: message.text and message.text.strip() in {str(texts['display_current_exchange_rate'].get(lang, '') or '').strip() for lang in texts['display_current_exchange_rate']})
async def view_rates(message: Message):
    usdt_rate = get_rate("USDT")
    btc_rate = get_rate("BTC")
    user_language = await get_user_language(message.from_user.id)
    # Проверка наличия курсов
    if usdt_rate is None or btc_rate is None:
        if user_language == "ru":
            await message.answer("❌ Ошибка: Курсы валют не найдены в базе данных.")
            return
        else :
            await message.answer("❌ Error: Exchange rates not found in database.")
            return
    if user_language == "ru":
        response = (
            f"💱 Текущие курсы валют:\n"
            f"1 VED = {usdt_rate} USDT\n"
            f"1 VED = {btc_rate} BTC\n\n"
            f"🔧 Чтобы изменить курс, используйте команду:\n"
            f"Введите: **Установка нового курса валют**\n"
            f"Затем укажите валюту и новый курс."
        )

        await message.answer(response)
    else :
        response = (
            f"💱 Current exchange rates:\n"
            f"1 VED = {usdt_rate} USDT\n"
            f"1 VED = {btc_rate} BTC\n\n"
            f"🔧 To change the rate, use the command:\n"
            f"Enter: **Setting a new exchange rate**\n"
            f"Then specify the currency and the new rate."
        )

        await message.answer(response)



@router.message(lambda message: message.text and message.text.strip() in {str(texts['show_pending_products'].get(lang, '') or '').strip() for lang in texts['show_pending_products']})
async def show_pending_products(message: Message):
    pending_products = get_pending_products()
    user_language = await get_user_language(message.from_user.id)
    if not pending_products:
        if user_language == "ru":
            await message.answer("Нет продуктов, ожидающих подтверждения.")
            return
        else :
            await message.answer("There are no products awaiting confirmation.")
            return

    for product in pending_products:
        # Если это объект sqlite3.Row, приводим его к словарю
        if isinstance(product, sqlite3.Row):
            product = dict(product)
        # Проверяем, что продукт — это словарь и что у него есть ID
        if 'id' not in product:
            continue
        if 'name' not in product or 'description' not in product or 'price' not in product:
            continue
        # Создаем инлайновые кнопки для подтверждения и отклонения
        approve_button = InlineKeyboardButton(text=texts['approve_button'].get(user_language, texts['approve_button']['en']), callback_data=f"approve_{product['id']}")
        reject_button = InlineKeyboardButton(text=texts['reject_button'].get(user_language, texts['reject_button']['en']), callback_data=f"reject_{product['id']}")

        # Создаем клавиатуру для каждого продукта
        inline_buttons = InlineKeyboardMarkup(inline_keyboard=[[approve_button, reject_button]])
        if user_language == "ru":
            # Добавляем информацию о продукте в текст
            product_text = "📝 Продукт, ожидающий подтверждения:\n\n"
            product_text += f"🔹 <b>{product['name']}</b>\n"
            product_text += f"📄 {product['description']}\n"
            product_text += f"💲 Цена: {product['price']}\n"
            product_text += f"💡 Статус: {product['status']}\n"
            product_text += f"📅 Подписка: {'Да' if product['is_subscription'] else 'Нет'}\n"
            if product['is_subscription']:
                product_text += f"🕒 Период подписки: {product.get('subscription_period', 'Не указан')}\n"
            product_text += f"🔑 Уникальный код: {product.get('code', 'Не указан')}\n"
            product_text += f"🖼 Изображение: {product.get('image', 'Нет')}\n"

            # Определяем название категории
            category_text = product.get('category', None)
            if category_text == 'session':
                category_text = 'Онлайн-сессия с терапевтом'
            elif category_text == 'retreat':
                category_text = 'Корпоративный ретрит'
            else:
                category_text = 'Не указана'  # Если категории нет или она не в ожидаемом формате

            product_text += f"📦 Категория: {category_text}\n"
            product_text += f"📍 Партнёр: {product.get('partner_id', 'Не указан')}\n"
            product_text += f"🔒 Скрыт: {'Да' if product['is_hidden'] else 'Нет'}\n"
            product_text += f"🎓 Курс ID: {product.get('course_id', 'Не указан')}\n"
            product_text += f"📅 После покупки: {product.get('after_purchase', 'Не указано')}\n\n"

            # Если есть изображение, отправляем фото
            if product.get("image"):
                await message.answer_photo(
                    photo=product["image"],
                    caption=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )
            else:
                # Если нет изображения, просто отправляем текст с кнопками
                await message.answer(
                    text=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )

        else :
            # Add product information to text
            product_text = "📝 Product awaiting confirmation:\n\n"
            product_text += f"🔹 <b>{product['name']}</b>\n"
            product_text += f"📄 {product['description']}\n"
            product_text += f"💲 Price: {product['price']}\n"
            product_text += f"💡 Status: {product['status']}\n"
            product_text += f"📅 Subscription: {'Yes' if product['is_subscription'] else 'No'}\n"
            if product['is_subscription']:
                product_text += f"🕒 Subscription Period: {product.get('subscription_period', 'Not specified')}\n"
            product_text += f"🔑 Unique code: {product.get('code', 'Not specified')}\n"
            product_text += f"🖼 Image: {product.get('image', 'None')}\n"

            # Define the category name
            category_text = product.get('category', None)
            if category_text == 'session':
                category_text = 'Online session with a therapist'
            elif category_text == 'retreat':
                category_text = 'Corporate retreat'
            else:
                category_text = 'Not specified'  # If the category is missing or not in the expected format

                product_text += f"📦 Category: {category_text}\n"
                product_text += f"📍 Partner: {product.get('partner_id', 'Not specified')}\n"
                product_text += f"🔒 Hidden: {'Yes' if product['is_hidden'] else 'No'}\n"
                product_text += f"🎓 Course ID: {product.get('course_id', 'Not specified')}\n"
                product_text += f"📅 After purchase: {product.get('after_purchase', 'Not specified')}\n\n"
            # If there is an image, send a photo
            if product.get("image"):
                await message.answer_photo(
                    photo=product["image"],
                    caption=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    text=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )


@router.callback_query(lambda c: c.data.startswith('approve_'))
async def approve_product(callback: CallbackQuery):
    product_id = int(callback.data.split('_')[1])  # Извлекаем id продукта
    update_product_status(product_id, 'approved')  # Обновляем статус
    user_language = await get_user_language(callback.from_user.id)
    # Получаем информацию о продукте для уведомления
    product = get_product_by_id(product_id)

    if user_language == "ru":
        await callback.message.answer(f"✅ Продукт '{product['name']}' одобрен и добавлен в каталог.")
    else :
        await callback.message.answer(f"✅ Product '{product['name']}' has been approved and added to the catalog.")


    # Убираем заявку (удаляем сообщение с заявкой)
    try:
        await callback.message.delete()
    except Exception as e:
        if user_language == "ru":
            print(f"Ошибка при удалении сообщения: {e}")
        else :
            print(f"Error deleting message: {e}")

    # Проверяем, содержит ли сообщение текст
    if callback.message.text:
        if user_language == "ru" :
            await callback.message.edit_text("\u2705 Продукт одобрен и добавлен в каталог.")
        else :
            await callback.message.edit_text("\u2705 Product approved and added to catalog.")
    elif callback.message.photo or callback.message.video or callback.message.document:
        if user_language == "ru":
            await callback.answer(
                "Продукт одобрен и добавлен в каталог. (Мультимедийное сообщение не может быть отредактировано.)")
        else :
            await callback.answer(
                "Product approved and added to catalog. (Multimedia message cannot be edited.)")
    else:
        await callback.answer("Не удалось отредактировать сообщение, так как оно не содержит текста.")

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith('reject_'))
async def reject_product(callback: CallbackQuery):
    user_language = await get_user_language(callback.from_user.id)
    product_id = int(callback.data.split('_')[1])  # Извлекаем id продукта
    update_product_status(product_id, 'rejected')  # Обновляем статус

    # Проверка, что сообщение содержит текст
    if callback.message.text:
        if user_language =="ru":
            await callback.message.edit_text("\u274c Продукт отклонён.")
        else :
            await callback.message.edit_text("\u274c Product rejected.")
    else:
        if user_language =="ru":
            await callback.message.answer("\u274c Продукт отклонён.")
        else :
            await callback.message.answer("\u274c Product rejected.")
    await callback.answer()

# Обработчик кнопки "Сделать рассылку"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['send_tag_broadcast'].get(lang, '') or '').strip() for lang in texts['send_tag_broadcast']})
async def admin_send_broadcast(message: types.Message):
    tags = get_all_tags()
    user_language = await get_user_language(message.from_user.id)
    if not tags:
        if user_language == "ru" :
            await message.answer("Тэги отсутствуют.")
        else :
            await message.answer("No tags.")
        return

    # Клавиатура для выбора тега
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tag, callback_data=f"broadcast_tag:{tag}")]
            for tag in tags
        ]
    )
    if user_language == "ru":
        await message.answer("Выберите тэг для рассылки:", reply_markup=keyboard)
    else :
        await message.answer("Select a tag for the newsletter:", reply_markup=keyboard)


# Обработчик выбора тега для рассылки
@router.callback_query(F.data.startswith("broadcast_tag:"))
async def process_broadcast(callback: CallbackQuery, state: FSMContext):
    tag = callback.data.split(":")[1]
    users = get_users_by_tag(tag)
    user_language = await get_user_language(callback.from_user.id)
    if not users:
        if user_language == "ru":
            await callback.answer("Нет подписчиков на этот тэг.")
        else :
            await callback.answer("No subscribers for this tag.")
        return

    # Сохраняем тэг и список пользователей в состояние
    await state.update_data(tag=tag, users=users)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    # Устанавливаем состояние ожидания сообщения
    await state.set_state(BroadcastState.waiting_for_message_admin)
    if user_language == "ru":
        await callback.message.answer(
            f"Отправьте сообщение для рассылки по тэгу '{tag}'."
        )
    else :
        await callback.message.answer(
            f"Send a message to the mailing list by tag '{tag}'."
        )


# Обработчик получения сообщения для рассылки
@router.message(BroadcastState.waiting_for_message_admin)
async def broadcast_message(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
        # Проверяем наличие ключей 'tag' и 'users' в состоянии
        tag = data.get('tag')
        users = data.get('users')

        if not tag or not users:
            if user_language == "ru":
                await message.answer("Ошибка: не удалось получить данные для рассылки.")
            else :
                await message.answer("Error: Failed to get data for mailing.")
            await state.clear()
            return

        sent_count = 0

        for user_id in users:
            try:
                await message.bot.send_message(
                    user_id,
                    f"🔔 Сообщение по тэгу '{tag}':\n{message.text}"
                )
                sent_count += 1
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

        await message.answer(f"Рассылка завершена. Отправлено сообщений: {sent_count}")

    except Exception as e:
        print(f"Ошибка во время рассылки: {e}")
        await message.answer("Произошла ошибка во время рассылки.")
    finally:
        # Завершаем состояние
        await state.clear()
# Состояния для FSM
class ReferralSystemStateTwo(StatesGroup):
    levels = State()  # Уровни реферальной системы
    rewards = State()  # Награды


# Обработчик кнопки для создания реферальной системы
@router.message(lambda message: message.text and message.text.strip() in {
    str(texts['create_referral_system'].get(lang, '') or '').strip() for lang in texts['create_referral_system']})
async def start_referral_creation(message: types.Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    await state.update_data(user_language=user_language)
    if user_language == "ru":
        await message.answer("Введите количество уровней реферальной системы:")
        await state.set_state(ReferralSystemStateTwo.levels)
    else :
        await message.answer("Enter the number of referral system levels:")
        await state.set_state(ReferralSystemStateTwo.levels)


# Обработчик для ввода количества уровней
@router.message(StateFilter(ReferralSystemStateTwo.levels))
async def set_levels(message: types.Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
        await state.update_data(user_language=user_language)
        levels = int(message.text)
        if levels <= 0:
            if user_language == "ru":
                await message.answer("Количество уровней должно быть положительным числом. Попробуйте снова.")
                return
            else :
                await message.answer("Number of levels must be a positive number. Try again.")
                return

        # Сохраняем количество уровней в состоянии
        await state.update_data(levels=levels)

        if user_language == "ru":
            await message.answer(
                f"Теперь введите награды для каждого уровня ({levels} уровней). Например, для первого уровня: 10,5 - где 10 - за покупку, а 5 - за выигрыш в лотереи."
                " Введите награды для каждого уровня в отдельной строке."
            )
            await state.set_state(ReferralSystemStateTwo.rewards)
        else :
            await message.answer(
                f"Now enter the rewards for each level ({levels} levels). For example, for the first level: 10.5 - where 10 is for a purchase, and 5 is for winning the lottery."
                " Enter the rewards for each level on a separate line."
            )
            await state.set_state(ReferralSystemStateTwo.rewards)

    except ValueError:
        if user_language == "ru":
            await message.answer("Введите корректное число для количества уровней.")
        else :
            await message.answer("Please enter a valid number for the number of levels.")

@router.message(StateFilter(ReferralSystemStateTwo.rewards))
async def set_rewards(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        levels = data.get("levels")
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
        # Разделяем введённые данные по строкам (каждая строка - для одного уровня)
        rewards = message.text.split("\n")

        # Проверяем, что количество введённых строк соответствует количеству уровней
        if len(rewards) != levels:
            if user_language == "ru":
                await message.answer(f"Вы должны ввести {levels} строки для {levels} уровней. Попробуйте снова.")
                return
            else :
                await message.answer(f"You must enter {levels} lines for {levels} levels. Try again.")
                return


        rewards_list = []
        for reward in rewards:
            # Разделяем каждую строку на 2 части (за покупку и выигрыш в лотерее)
            reward_parts = reward.split(",")
            if len(reward_parts) != 2:
                if user_language == "ru":
                    await message.answer(
                        f"Награды для уровня должны быть в формате 'X, Y' (где X - за покупку, Y - за выигрыш в лотерее). Пример: '20, 50'.")
                    return
                else :
                    await message.answer(
                        f"Rewards for a level should be in the format 'X, Y' (where X is for a purchase, Y is for winning a lottery). Example: '20, 50'.")
                    return
            try:
                rewards_list.append([int(reward_part.strip()) for reward_part in reward_parts])
            except ValueError:
                if user_language =="ru":
                    await message.answer(f"Введите корректные числовые значения для наград. Пример: '20, 50'.")
                    return
            else :
                await message.answer(f"Please enter valid numeric values ​​for rewards. Example: '20, 50'.")
                return

        # Сохраняем награды в состоянии
        await state.update_data(rewards=rewards_list)

        # Вызываем создание реферальной системы
        create_referral_system(levels, rewards_list)

        if user_language == "ru":
            await message.answer(f"Реферальная система создана:\nУровни: {levels}\nНаграды: {rewards_list}")
            await state.clear()
        else :
            await message.answer(f"Referral system created:\nLevels: {levels}\nRewards: {rewards_list}")
            await state.clear()


    except ValueError:
        if user_language =="ru":
            await message.answer("Введите корректные значения для наград (например, '20, 50' для каждого уровня).")
        else :
            await message.answer("Please enter valid values ​​for rewards (e.g. '20, 50' for each level).")


class ReferralSystemState(StatesGroup):
    levels = State()  # Уровни реферальной системы
    rewards = State()  # Награды
    edit_level = State()  # Редактирование уровня
    edit_purchase = State()  # Редактирование награды за покупку
    edit_lottery = State()  # Редактирование награды за лотерею

# Обработчик кнопки для редактирования реферальной системы
@router.message(lambda message: message.text and any(
    message.text.strip() == str(texts['edit_referral_system'].get(lang, '')).strip() for lang in texts['edit_referral_system']
))
async def start_referral_editing(message: types.Message, state: FSMContext):
    user_language = get_user_language(message.from_user.id)  # Получаем язык пользователя
    current_system = get_current_referral_system()
    current_levels = current_system['levels']
    current_rewards = current_system['rewards']

    rewards_text = "\n".join(
        f"Уровень {level}: Покупка {rewards[0]}, Лотерея {rewards[1]}" if user_language == "ru"
        else f"Level {level}: Purchase {rewards[0]}, Lottery {rewards[1]}"
        for level, rewards in current_rewards.items()
    )

    inline_keyboard = [
        [InlineKeyboardButton(
            text=f"Уровень {level}" if user_language == "ru" else f"Level {level}",
            callback_data=f"edit_reward_{level}"
        )]
        for level in current_rewards.keys()
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    await message.answer(
        f"Текущие настройки:\nУровни: {current_levels}\nНаграды:\n{rewards_text}\n\nВыберите уровень для изменения награды:"
        if user_language == "ru" else
        f"Current settings:\nLevels: {current_levels}\nRewards:\n{rewards_text}\n\nSelect a level to edit the reward:",
        reply_markup=keyboard
    )

    await state.set_state(ReferralSystemState.edit_level)
    await state.update_data(current_system=current_system)

# Обработчик для выбора уровня
@router.callback_query(lambda callback: callback.data.startswith("edit_reward_"))
async def edit_reward_callback(query: types.CallbackQuery, state: FSMContext):
    user_language = get_user_language(query.from_user.id)
    level = int(query.data.split("_")[-1])

    inline_keyboard = [
        [
            InlineKeyboardButton(
                text="Покупка Бонус" if user_language == "ru" else "Purchase Bonus",
                callback_data=f"edit_purchase_{level}"
            ),
            InlineKeyboardButton(
                text="Лотерея" if user_language == "ru" else "Lottery",
                callback_data=f"edit_lottery_{level}"
            )
        ],
        [InlineKeyboardButton(
            text="Отмена" if user_language == "ru" else "Cancel",
            callback_data="cancel"
        )]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard, row_width=2)

    await query.message.edit_text(
        f"Вы выбрали уровень {level}. Выберите награду для изменения:" if user_language == "ru"
        else f"You have selected level {level}. Choose the reward to edit:",
        reply_markup=keyboard
    )
    await state.update_data(edit_level=level)

# Обработчик для изменения награды за покупку
@router.callback_query(lambda callback: callback.data.startswith("edit_purchase_"))
async def edit_purchase_callback(query: types.CallbackQuery, state: FSMContext):
    user_language = get_user_language(query.from_user.id)
    level = int(query.data.split("_")[-1])
    await query.message.edit_text(
        f"Введите новую награду за покупку для уровня {level}:" if user_language == "ru"
        else f"Enter the new purchase reward for level {level}:"
    )
    await state.set_state(ReferralSystemState.edit_purchase)

# Обработчик для изменения награды за лотерею
@router.callback_query(lambda callback: callback.data.startswith("edit_lottery_"))
async def edit_lottery_callback(query: types.CallbackQuery, state: FSMContext):
    user_language = get_user_language(query.from_user.id)
    level = int(query.data.split("_")[-1])
    await query.message.edit_text(
        f"Введите новую награду за лотерею для уровня {level}:" if user_language == "ru"
        else f"Enter the new lottery reward for level {level}:"
    )
    await state.set_state(ReferralSystemState.edit_lottery)

# Обработчик ввода новой награды за покупку
@router.message(StateFilter(ReferralSystemState.edit_purchase))
async def set_new_purchase_reward(message: types.Message, state: FSMContext):
    user_language = get_user_language(message.from_user.id)
    try:
        new_reward = int(message.text.strip())
        data = await state.get_data()
        level = data['edit_level']
        current_system = data['current_system']
        current_system['rewards'][level][0] = new_reward
        await state.update_data(current_system=current_system)
        update_referral_rewards(level, current_system['rewards'][level])  # Обновляем в БД

        await message.answer(
            f"Новая награда за покупку для уровня {level} установлена: {new_reward}." if user_language == "ru"
            else f"New purchase reward for level {level} set to: {new_reward}."
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректное число для награды." if user_language == "ru"
            else "Please enter a valid number for the reward."
        )

# Обработчик ввода новой награды за лотерею
@router.message(StateFilter(ReferralSystemState.edit_lottery))
async def set_new_lottery_reward(message: types.Message, state: FSMContext):
    user_language = get_user_language(message.from_user.id)
    try:
        new_reward = int(message.text.strip())
        data = await state.get_data()
        level = data['edit_level']
        current_system = data['current_system']
        current_system['rewards'][level][1] = new_reward
        await state.update_data(current_system=current_system)
        update_referral_rewards(level, current_system['rewards'][level])  # Обновляем в БД

        await message.answer(
            f"Новая награда за лотерею для уровня {level} установлена: {new_reward}." if user_language == "ru"
            else f"New lottery reward for level {level} set to: {new_reward}."
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректное число для награды." if user_language == "ru"
            else "Please enter a valid number for the reward."
        )

# Обработчик кнопки "Отмена"
@router.callback_query(lambda callback: callback.data.startswith("cancel"))
async def cancel_editing(query: types.CallbackQuery, state: FSMContext):
    user_language = get_user_language(query.from_user.id)
    await query.message.edit_text(
        "Редактирование отменено." if user_language == "ru"
        else "Editing cancelled."
    )
    await state.clear()

# Обработка нажатия на кнопку "Сделать рассылку по продукту"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['send_product_broadcast'].get(lang, '') or '').strip() for lang in texts['send_product_broadcast']})
async def send_product_message(msg: types.Message):
    user_language = "ru"  # Предположим, что язык пользователя уже определен

    # Получаем все продукты из базы данных
    products = get_all_products_two()

    # Создаем инлайн-кнопки для каждого продукта
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[])
    for product in products:
        button = InlineKeyboardButton(
            text=f"ID:{product['id']} - {product['name']}",
            callback_data=f"send_product_{product['id']}"
        )
        keyboard.inline_keyboard.append([button])

    # Отправляем сообщение с кнопками
    if user_language == "ru":
        await msg.answer("Выберите продукт для рассылки:", reply_markup=keyboard)
    else:
        await msg.answer("Select a product for the broadcast:", reply_markup=keyboard)

# Обработка выбора продукта
@router.callback_query(lambda c: c.data.startswith('send_product_'))
async def handle_product_selection(callback_query: types.CallbackQuery, state: FSMContext):
    user_language = "ru"  # Предположим, что язык пользователя уже определен
    product_id = int(callback_query.data.split('_')[2])

    # Сохраняем ID выбранного продукта в состоянии
    await state.update_data(product_id=product_id)

    # Запрашиваем сообщение для рассылки
    if user_language == "ru":
        await callback_query.answer("Введите сообщение для рассылки по продукту.")
        await callback_query.bot.send_message(
            callback_query.from_user.id,
            "Введите текст сообщения, которое вы хотите отправить всем пользователям, купившим этот продукт."
        )
    else:
        await callback_query.answer("Enter the message for the product broadcast.")
        await callback_query.bot.send_message(
            callback_query.from_user.id,
            "Enter the text of the message you want to send to all users who purchased this product."
        )

    # Переходим в состояние ожидания ввода сообщения
    await state.set_state(ProductMessageState.waiting_for_message)

# Обработка ввода сообщения
@router.message(ProductMessageState.waiting_for_message)
async def process_message_for_product(msg: types.Message, state: FSMContext):
    user_language = "ru"  # Предположим, что язык пользователя уже определен
    user_data = await state.get_data()
    product_id = user_data.get('product_id')
    message_text = msg.text

    # Логика для рассылки по продукту
    users = get_users_by_product(product_id)

    # Рассылка сообщения пользователям
    for user in users:
        try:
            await msg.bot.send_message(user['user_id'], message_text)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user['user_id']}: {e}")

    # Информируем администратора, что рассылка завершена
    if user_language == "ru":
        await msg.answer("Рассылка по продукту завершена.")
    else:
        await msg.answer("Product broadcast completed.")

    # Завершаем состояние
    await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_all_products'].get(lang, '') or '').strip() for lang in texts['view_all_products']})
async def send_product_page(message):
    chat_id = message.chat.id  # Извлекаем chat_id из объекта message
    page = 1  # Страница по умолчанию

    products = get_all_products()  # Получаем список продуктов
    # Фильтруем только те продукты, которые не скрыты и имеют статус approved
    visible_products = [
        p for p in products
        if p.get("status") == "approved"  # Правильная фильтрация
    ]

    total_pages = ceil(len(visible_products) / ITEMS_PER_PAGE)  # Количество страниц
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    products_to_show = visible_products[start_index:end_index]

    text = "📋 Список продуктов:\n\n"
    for product in products_to_show:
        name = product["name"] if not product.get("is_personal") else "Продукт доступен по коду"
        text += f"🔹 {name} — {product['price']} VED\n"

    keyboard_buttons = []

    for product in products_to_show:
        button_text = f"ℹ {product['name']} - {product['price']} VED"
        callback_data = f"info_admin_{product['id']}"  # Используем ID продукта
        keyboard_buttons.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page-1}"))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"page_{page+1}"))

    keyboard_buttons.extend(navigation_buttons)
    keyboard_buttons.append(InlineKeyboardButton(text="🔍 Поиск по коду", callback_data="search_product_by_code_admin"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[keyboard_buttons])

    await message.bot.send_message(chat_id, text, reply_markup=keyboard)

# Пагинация продуктов
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


@router.callback_query(lambda callback: callback.data == "search_product_by_code_admin")
async def search_product_by_code_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код продукта для поиска.")  # Запрашиваем код продукта
    await state.set_state("search_product_by_code")  # Устанавливаем состояние, чтобы ожидать код
    await callback.answer()  # Ответ на инлайн кнопку


@router.callback_query(lambda callback: callback.data.startswith("info_admin_"))
async def product_info_handler(callback: CallbackQuery):
    try:
        callback_data_parts = callback.data.split("_")
        if len(callback_data_parts) < 3:
            raise ValueError("Некорректные данные callback.")
        product_id = int(callback_data_parts[2])  # Извлекаем ID продукта
    except (IndexError, ValueError) as e:
        await callback.message.answer("❌ Ошибка в данных продукта.")
        print(f"Ошибка при извлечении ID продукта: {e}")
        return

    # Получаем продукт и информацию о пользователе
    product = get_product_by_id(product_id)
    if not product:
        await callback.message.answer("❌ Продукт не найден.")
        print(f"Продукт с ID {product_id} не найден.")
        return
    user_id = callback.from_user.id
    user_balance = await get_user_balance(user_id)  # Обновлено: функция асинхронная

    if not product:
        await callback.message.answer("❌ Продукт не найден.")
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

    # Формируем сообщение о продукте
    product_text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 Цена: {product['price']} VED\n"
        f"📋 Категория: {category_text}\n"
        f"🔖 Статус: {subscription_text}\n"
        f"💳 Ваш баланс: {user_balance} VED"
    )

    # Создаем клавиатуру с кнопкой "Купить", если у пользователя хватает средств
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if user_balance >= product["price"]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="🛒 Купить",
                callback_data=f"buy_product_{product_id}"
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

# Получаем заявки на партнёрство
@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_partner_applications'].get(lang, '') or '').strip() for lang in texts['view_partner_applications']})
async def show_partnership_requests(message: types.Message):
    user_language = await get_user_language(message.from_user.id)  # Предположим, что язык пользователя уже определен

    # Получаем все заявки на партнёрство со статусом 'pending'
    partners = get_partners_with_status('pending')
    if not partners:
        if user_language == "ru":
            await message.answer("Нет заявок на партнёрство.", reply_markup=admin_menu())
        else:
            await message.answer("No partnership applications.", reply_markup=admin_menu())
        return

    # Формируем сообщение с заявками
    for partner in partners:
        partner_id = partner[0]
        partner_name = partner[1]
        partner_credo = partner[2]
        partner_logo_url = partner[3]
        partner_show_in_list = partner[4]
        partner_status = partner[5]
        partner_real_id = partner[6]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"Принять {partner_name}" if user_language == "ru" else f"Accept {partner_name}",
                callback_data=f"accept_{partner_real_id}"
            ),
            InlineKeyboardButton(
                text=f"Отклонить {partner_name}" if user_language == "ru" else f"Reject {partner_name}",
                callback_data=f"mem_{partner_real_id}"
            )
        ]])

        caption = (
            f"Заявка от {partner_name}.\nКредо: {partner_credo}\n"
            f"Показать в списке: {'Да' if partner_show_in_list else 'Нет'}\n"
            f"Статус: {partner_status}"
            if user_language == "ru"
            else
            f"Application from {partner_name}.\nCredo: {partner_credo}\n"
            f"Show in list: {'Yes' if partner_show_in_list else 'No'}\n"
            f"Status: {partner_status}"
        )

        if partner_logo_url:
            await message.answer_photo(photo=partner_logo_url, caption=caption, reply_markup=keyboard)
        else:
            await message.answer(caption, reply_markup=keyboard)

# Обработка принятия или отклонения заявки
@router.callback_query(lambda c: c.data.startswith("accept_") or c.data.startswith("mem_"))
async def handle_partnership_action(callback_query: types.CallbackQuery):
    user_language = await get_user_language(callback_query.from_user.id)  # Предположим, что язык пользователя уже определен
    action = callback_query.data.split('_')[0]
    user_id = int(callback_query.data.split('_')[1])

    logging.debug(f"Действие: {action}, user_id: {user_id}")

    user = get_user_by_id_admin(user_id)
    if not user:
        logging.error(f"Не удалось найти пользователя с user_id {user_id}.")
        await callback_query.answer(
            "Не удалось найти пользователя." if user_language == "ru" else "Could not find the user."
        )
        return

    logging.debug(f"Пользователь найден: ID={user['user_id']}, Role={user['role']}")

    if action == "accept":
        partner_id = user_id
        update_partner_status(partner_id, 'approved')
        if user['role'] != 'admin':
            update_user_role_for_partner(user_id, 'partner')
            logging.info(f"Роль пользователя с ID {user_id} изменена на 'partner'.")

        await callback_query.answer(
            "Заявка принята и роль обновлена." if user_language == "ru" else "Application accepted and role updated."
        )
        logging.info(f"Заявка от пользователя с ID {user_id} принята.")
    elif action == "mem":
        partner_id = user_id
        update_partner_status(partner_id, 'rejected')
        await callback_query.answer(
            f"Заявка от {partner_id} отклонена." if user_language == "ru" else f"Application from {partner_id} rejected."
        )

    await show_partnership_requests(callback_query.message)
    logging.debug("Отправлен обновлённый список заявок.")


@router.message(lambda message: message.text and message.text.strip() in {str(texts['support_requests'].get(lang, '') or '').strip() for lang in texts['support_requests']})
async def view_feedbacks(message: types.Message):
    user_language = await get_user_language(message.from_user.id)
    feedbacks = get_feedbacks()

    if user_language == "ru":
        response_text = "Обращения в поддержку:\n\n"
    else :
        response_text = "Support requests:\n\n"
    for feedback in feedbacks:
        user_id, feedback_text, created_at = feedback
        if user_language == "ru":
            response_text += f"USER_ID: {user_id}\nОбращение:{feedback_text}\n{created_at}\n\n"
        else :
            response_text += f"USER_ID: {user_id}\nRequest:{feedback_text}\n{created_at}\n\n"

    # Отправляем текст админу
    await message.answer(response_text)



@router.message(lambda message: message.text and message.text.strip() in {str(texts['delete_aforism'].get(lang, '') or '').strip() for lang in texts['delete_aforism']})
async def cmd_delete_aphorism(message: types.Message, state: FSMContext):
    # Получаем список всех афоризмов из базы данных
    aphorisms = get_all_aphorisms()
    user_language = await get_user_language(message.from_user.id)
    if not aphorisms:
        if user_language == "ru":
            await message.answer("В базе данных нет афоризмов для удаления.")
            return
        else :
            await message.answer("There are no aphorisms in the database to delete.")
            return

    await state.update_data(user_language=user_language)
    if user_language == 'ru':
        aphorisms_text = "Список афоризмов:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Автор: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)
    else :
        aphorisms_text = "List of aphorisms:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Author: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)


    if user_language == "ru":
        await message.answer("Пожалуйста, введите ID афоризма, который вы хотите удалить:")
        await state.set_state(DeleteAphorism.waiting_for_id)
    else :
        await message.answer("Please enter the ID of the aphorism you want to delete:")


# Принимаем ID афоризма и удаляем его
@router.message(DeleteAphorism.waiting_for_id)
async def process_aphorism_id(message: types.Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")
        aphorism_id = int(message.text)
        # Проверяем, существует ли афоризм с указанным ID
        if not aphorism_exists(aphorism_id):
            if user_language == 'ru':
                await message.answer("Афоризм с таким ID не найден. Убедитесь, что вы ввели правильный ID.")
            else :
                await message.answer("Aphorism with such ID was not found. Make sure you entered the correct ID.")
        else:
            # Удаляем афоризм из базы данных
            delete_aphorism(aphorism_id)
            if user_language == "ru":
                await message.answer("Афоризм был успешно удалён!")
            else :
                await message.answer("The aphorism was successfully deleted!")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный числовой ID.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при удалении афоризма: {e}")
    finally:
        await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['edit_aforism'].get(lang, '') or '').strip() for lang in texts['edit_aforism']})
async def cmd_edit_aphorism(message: types.Message, state: FSMContext):
    # Получаем список всех афоризмов
    aphorisms = get_all_aphorisms()
    user_language = await get_user_language(message.from_user.id)
    await state.update_data(user_language=user_language)
    if not aphorisms:
        if user_language == "ru":
            await message.answer("В базе данных нет афоризмов для изменения.")
            return
        else :
            await message.answer("There are no aphorisms in the database to change.")
            return

    # Формируем список афоризмов для выбора
    if user_language == "ru":
        aphorisms_text = "Список афоризмов:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Автор: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)
    else :
        aphorisms_text = "List of aphorisms:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Author: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)


    # Просим ввести ID афоризма для изменения
    if user_language == "ru":
        await message.answer("Пожалуйста, введите ID афоризма, который вы хотите изменить:")
        await state.set_state(EditAphorism.waiting_for_id)
    else :
        await message.answer("Please enter the ID of the aphorism you want to edit:")
        await state.set_state(EditAphorism.waiting_for_id)

# Получаем ID афоризма
@router.message(EditAphorism.waiting_for_id)
async def process_edit_aphorism_id(message: types.Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")
        await state.update_data(user_language=user_language)
        aphorism_id = int(message.text)

        if not aphorism_exists(aphorism_id):
            if user_language == "ru":
                await message.answer("Афоризм с таким ID не найден. Убедитесь, что вы ввели правильный ID.")
                return
            else:
                await message.answer("Aphorism with such ID was not found. Make sure you entered the correct ID.")
                return

        # Сохраняем ID афоризма в состоянии
        await state.update_data(aphorism_id=aphorism_id)

        if user_language == "ru":
            await message.answer("Что вы хотите изменить?\n\n1. Текст\n2. Автора\n\nВведите 1 или 2:")
            await state.set_state(EditAphorism.waiting_for_choice)
        else :
            await message.answer("What do you want to change?\n\n1. Text\n2. Author\n\nEnter 1 or 2:")
            await state.set_state(EditAphorism.waiting_for_choice)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный числовой ID.")

# Получаем выбор: текст или автор
@router.message(EditAphorism.waiting_for_choice)
async def process_edit_choice(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    choice = message.text.strip()

    if choice == "1":
        if user_language == "ru":
            await message.answer("Введите новый текст афоризма:")
            await state.set_state(EditAphorism.waiting_for_new_text)
        else :
            await message.answer("Enter new aphorism text:")
            await state.set_state(EditAphorism.waiting_for_new_text)
    elif choice == "2":
        if user_language == "ru":
            await message.answer("Введите нового автора афоризма:")
            await state.set_state(EditAphorism.waiting_for_new_author)
        else :
            await message.answer("Enter a new aphorism author:")
            await state.set_state(EditAphorism.waiting_for_new_author)
    else:
        if user_language == "ru" :
            await message.answer("Пожалуйста, введите 1 или 2 для выбора.")
        else :
            await message.answer("Please enter 1 or 2 to choose.")

# Обновляем текст афоризма
@router.message(EditAphorism.waiting_for_new_text)
async def process_new_text(message: types.Message, state: FSMContext):
    new_text = message.text
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    data = await state.get_data()
    aphorism_id = data['aphorism_id']

    update_aphorism_text(aphorism_id, new_text)
    if user_language == "ru":
        await message.answer("Текст афоризма был успешно обновлён!")
        await state.clear()
    else :
        await message.answer("The aphorism text was successfully updated!")
        await state.clear()


# Обновляем автора афоризма
@router.message(EditAphorism.waiting_for_new_author)
async def process_new_author(message: types.Message, state: FSMContext):
    new_author = message.text
    data = await state.get_data()
    aphorism_id = data['aphorism_id']
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    update_aphorism_author(aphorism_id, new_author)
    if user_language == 'ru':
        await message.answer("Автор афоризма был успешно обновлён!")
        await state.clear()
    else :
        await message.answer("The author of the aphorism was successfully updated!")
        await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_all_users'].get(lang, '') or '').strip() for lang in texts['view_all_users']})
async def show_all_users(message: types.Message):
    # Получаем список пользователей из базы данных
    users = get_all_users()
    user_language = await get_user_language(message.from_user.id)
    if not users:
        if user_language == "ru":
            await message.answer("Пользователей пока нет.")
    else:
        if user_language == "ru":
            user_list = "\n".join([f"ID: {user['user_id']}, Имя: {user['username']}" for user in users])
            await message.answer(f"Список пользователей:\n{user_list}")
        else :
            user_list = "\n".join([f"ID: {user['user_id']}, Name: {user['username']}" for user in users])
            await message.answer(f"User list:\n{user_list}")



# Хендлер нажатия на кнопку "Добавить пользователю баланс"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_balance_to_user'].get(lang, '') or '').strip() for lang in texts['add_balance_to_user']})
async def start_add_balance(message: types.Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    if user_language == "ru":
        await message.answer("Введите ID пользователя, которому нужно добавить баланс:")
        await state.set_state(AddBalanceStates.waiting_for_user_id)
    else :
        await message.answer("Enter the ID of the user you want to add balance to:")
        await state.set_state(AddBalanceStates.waiting_for_user_id)



# Хендлер ввода ID пользователя
@router.message(AddBalanceStates.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID пользователя должно быть числом. Попробуйте ещё раз:")
        return

    await state.update_data(user_id=int(message.text))
    await message.answer("Введите сумму, на которую нужно увеличить баланс:")
    await state.set_state(AddBalanceStates.waiting_for_amount)


# Хендлер ввода суммы
@router.message(AddBalanceStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Сумма должна быть числом. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    user_id = data["user_id"]
    amount = int(message.text)

    # Добавляем баланс пользователю
    if add_balance_to_user(user_id, amount):
        await message.answer(f"Баланс пользователя с ID {user_id} успешно увеличен на {amount}.")
    else:
        await message.answer(f"Ошибка: Пользователь с ID {user_id} не найден.")

    await state.clear()

@router.message(lambda message: message.text and message.text.strip() in {str(texts['start_lottery'].get(lang, '') or '').strip() for lang in texts['start_lottery']})
async def start_lottery(message: types.Message):
    with connect_db() as conn:
        cursor = conn.cursor()

        # Завершаем предыдущую лотерею
        cursor.execute("UPDATE lottery SET active = 0 WHERE active = 1")

        # Создаем новую лотерею
        cursor.execute(
            "INSERT INTO lottery (name, ticket_price, fund, active) VALUES (?, ?, ?, ?)",
            ("Месячная лотерея", 0, 0, 1)
        )
        lottery_id = cursor.lastrowid

        # Список для генерации билетов
        tickets = []

        # Генерация выигрышных билетов по категориям
        categories = [
            {'count': 9, 'prize': '10%', 'probability': 0.1},
            {'count': 9, 'prize': '1%', 'probability': 0.01},
            {'count': 9, 'prize': '0.1%', 'probability': 0.001},
            {'count': 9, 'prize': '0.01%', 'probability': 0.0001},
            {'count': 9, 'prize': '0.001%', 'probability': 0.00001},
            {'count': 9, 'prize': '0.0001%', 'probability': 0.000001},
        ]

        # Генерация 54 выигрышных билетов
        winning_tickets = random.sample(range(1, 1001), 54)  # 54 выигрышных билета
        winning_categories = []

        # Присваиваем категории победителям
        for i in range(9):
            winning_categories.append('10%')
        for i in range(9):
            winning_categories.append('1%')
        for i in range(9):
            winning_categories.append('0.1%')
        for i in range(9):
            winning_categories.append('0.01%')
        for i in range(9):
            winning_categories.append('0.001%')
        for i in range(9):
            winning_categories.append('0.0001%')

        # Перемешиваем категории для случайного распределения
        random.shuffle(winning_categories)

        # Помечаем выигрышные билеты
        ticket_map = dict(zip(winning_tickets, winning_categories))

        # Генерация списка всех билетов
        for ticket_number in range(1, 1001):
            if ticket_number in ticket_map:
                prize = ticket_map[ticket_number]
                tickets.append((lottery_id, None, None, ticket_number, 1, prize))
            elif len(tickets) < 446:  # 446 повторных попыток
                tickets.append((lottery_id, None, None, ticket_number, 0, "Повторная попытка"))
            else:  # 500 пустых
                tickets.append((lottery_id, None, None, ticket_number, 0, "Пустой"))

        # Вставка сгенерированных билетов в базу данных
        cursor.executemany(
            "INSERT INTO lottery_tickets (lottery_id, user_id, username, ticket_number, is_winner, prize) VALUES (?, ?, ?, ?, ?, ?)",
            tickets
        )

        conn.commit()

    await message.reply("Лотерея началась, билеты сгенерированы!")


@router.message(lambda message: message.text and message.text.strip() in {str(texts['end_lottery'].get(lang, '') or '').strip() for lang in texts['end_lottery']})
async def end_lottery(message: types.Message):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE lottery SET active = 0 WHERE active = 1")
        conn.commit()
    await message.reply("Лотерея завершена.")

@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_lottery_participants'].get(lang, '') or '').strip() for lang in texts['view_lottery_participants']})
async def view_lottery_participants(message: types.Message):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ticket_number, username, user_id FROM lottery_tickets WHERE user_id IS NOT NULL"
        )
        participants = cursor.fetchall()
    if participants:
        response = "\n".join([f"Билет #{ticket[0]}: @{ticket[1]} (ID: {ticket[2]})" for ticket in participants])
    else:
        response = "Участников пока нет."
    await message.reply(response)

class TicketPriceState(StatesGroup):
    waiting_for_price = State()

@router.message(lambda message: message.text and message.text.strip() in {str(texts['set_lottery_ticket_price'].get(lang, '') or '').strip() for lang in texts['set_lottery_ticket_price']})
async def set_ticket_price(message: types.Message, state: FSMContext):
    await message.reply(
        "Введите цену за билет (целое число):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TicketPriceState.waiting_for_price)

@router.message(TicketPriceState.waiting_for_price)
async def process_ticket_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError("Некорректная цена.")

        # Обновляем цену билета в базе данных
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE lottery SET ticket_price = ? WHERE active = 1", (price,))
            conn.commit()

        await message.reply(f"Цена за билет успешно установлена: {price} VED.")
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректную цену (целое число больше нуля):")

@router.message(lambda message: message.text and message.text.strip() in {str(texts['file_command'].get(lang, '') or '').strip() for lang in texts['file_command']})
async def send_file(message: types.Message):
    if os.path.exists(FILE_PATH):
        # Открываем файл в бинарном режиме
        with open(FILE_PATH, 'rb') as file:
            # Передаем файл как BufferedInputFile
            input_file = BufferedInputFile(file.read(), filename="texts.xlsx")  # Передаем байтовый поток
            await message.bot.send_document(message.chat.id, input_file)
    else:
        await message.answer("Файл с командами не найден.")


@router.message(lambda message: message.text and message.text.strip() in {str(texts['new_file_command'].get(lang, '') or '').strip() for lang in texts['new_file_command']})
async def new_file_command(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте файл в формате .xlsx.")
    # Устанавливаем состояние с использованием await state.set_state()
    await state.set_state(FileUpdateState.waiting_for_file)


@router.message(FileUpdateState.waiting_for_file)
async def update_file(message: types.Message, state: FSMContext):
    if message.document and message.document.mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        # Проверяем, существует ли файл, перед его удалением
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)

        # Загружаем новый файл
        new_file = await message.bot.get_file(message.document.file_id)
        await message.bot.download_file(new_file.file_path, FILE_PATH)

        await message.answer("Файл с командами обновлён.")
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправьте файл в формате .xlsx.")


