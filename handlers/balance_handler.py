
from aiogram import Router, types,F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton,ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import (get_user_balance, get_exchange_rate, get_user_language, update_balance, get_admins,
                      get_user_balance_perevod, get_user_for_perevod, update_user_balance_perevod,load_texts,get_user_balance_perevod_by_id,get_username_by_id)# Ваши функции работы с БД
from config import CURRENCY, BTCAddr  # Импортируем необходимые данные из конфигурации
from handlers.menu_handler import back_to_main_menu
from handlers.add_product_handler import cancel_process,cancel_keyboard
import requests
router = Router()

# Состояния для FSM
class TransferState(StatesGroup):
    waiting_for_username = State()
    waiting_for_amount = State()

class BalanceStates(StatesGroup):
    waiting_for_deposit_method = State()
    waiting_for_deposit_amount = State()
    waiting_for_usdt_confirmation = State()  # Подтверждение пополнения через USDT
    waiting_for_btc_confirmation = State()  # Новое состояние для BTC
import logging
# Настроим логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
texts = load_texts('texts.xlsx')


@router.message(lambda message: message.text and message.text.strip() in {str(texts['balance_button'].get(lang, '') or '').strip() for lang in texts['balance_button']})

async def balance_button_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_language = await get_user_language(message.from_user.id)
    # Логирование начала работы обработчика

        # Получаем баланс пользователя
    balance = await get_user_balance(user_id)
    balance_message = texts['balance_message'][user_language].format(balance=balance)

        # Создаем клавиатуру с кнопками для пополнения баланса, вывода средств и перевода
    balance_buttons = [
            [KeyboardButton(text=texts['replenish_balance_button'][user_language]),
             KeyboardButton(text=texts['withdraw_funds_button'][user_language])],
            [KeyboardButton(text=texts['transfer_funds_button'][user_language])],
            [KeyboardButton(text=texts['back_to_main_menu_button'][user_language])]
    ]
    balance_markup = ReplyKeyboardMarkup(keyboard=balance_buttons, resize_keyboard=True)

        # Отправка сообщения с балансом и клавиатурой
    await message.answer(balance_message, reply_markup=balance_markup)

        # Логирование перед очисткой состояния
    logger.debug(f"Очистка состояния для пользователя {user_id}")
    await state.clear()  # Очистка состояния после ответа
    # Логирование окончания работы обработчика
    logger.debug(f"Завершение обработки кнопки для пользователя {user_id}")



# Обработчик кнопки "Пополнить баланс"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['replenish_balance_button'].get(lang, '') or '').strip() for lang in texts['replenish_balance_button']})
async def deposit_button_handler(message: Message, state: FSMContext):
    # Получаем язык пользователя из состояния (по умолчанию русский)
    user_language = (await state.get_data()).get('language', 'ru')

    # Текстовые ключи для методов пополнения
    deposit_methods_keys = ['usdt', 'btc', 'yumoney', 'moneygram', 'back_to_main_menu_button']
    deposit_methods = [texts[key][user_language] for key in deposit_methods_keys]

    method_buttons = [[KeyboardButton(text=method)] for method in deposit_methods]
    method_markup = ReplyKeyboardMarkup(keyboard=method_buttons, resize_keyboard=True)

    await state.set_state(BalanceStates.waiting_for_deposit_method)
    await message.answer(texts['select_deposit_method'][user_language], reply_markup=method_markup)


# Обработчик выбора способа пополнения
@router.message(BalanceStates.waiting_for_deposit_method)
async def deposit_method_handler(message: Message, state: FSMContext):
    user_language = (await state.get_data()).get('language', 'ru')
    selected_method = message.text
    await state.update_data(deposit_method=selected_method)

    if selected_method == texts['usdt'][user_language]:
        wallet_address = "TEQ2SxzwzNUNDdRcPHttGCYBpkr1VP1b7b"  # Укажите ваш адрес для USDT
        message_text = texts['usdt_deposit_message'][user_language].format(wallet_address=wallet_address)
        await state.set_state(BalanceStates.waiting_for_deposit_amount)
        await message.answer(f"{message_text}\n\n{texts['enter_deposit_amount'][user_language]}")
    elif selected_method == texts['btc'][user_language]:
        wallet_address = "0x270d51b6f2906a7d7150e4d70c2d627949917f12"  # Адрес из конфигурации
        message_text = texts['btc_deposit_message'][user_language].format(wallet_address=wallet_address)
        await state.set_state(BalanceStates.waiting_for_deposit_amount)
        await message.answer(f"{message_text}\n\n{texts['enter_deposit_amount'][user_language]}")
    elif selected_method == texts['back_to_main_menu'][user_language]:
        await back_to_main_menu(message, state)
        await state.clear()
    else:
        await message.answer(texts['method_not_implemented'][user_language])
        await state.clear()


@router.message(BalanceStates.waiting_for_deposit_amount)
async def deposit_amount_handler(message: Message, state: FSMContext):
    user_language = (await state.get_data()).get('language', 'ru')

    try:
        amount = message.text.replace(',', '.', 1)
        if not amount.replace('.', '', 1).isdigit():
            raise ValueError(texts['invalid_amount_format'][user_language])

        amount = float(amount)
        if amount <= 0:
            raise ValueError(texts['invalid_amount'][user_language])
    except ValueError as e:
        await message.answer(str(e))
        return

    user_data = await state.get_data()
    selected_method = user_data.get("deposit_method")
    exchange_rate = await get_exchange_rate(selected_method)

    if selected_method in [texts['usdt'][user_language], texts['btc'][user_language]]:
        confirmation_message = texts['deposit_confirmation_message'][user_language].format(
            method=selected_method,
            amount=amount,
            exchange_rate=exchange_rate
        )
        await state.update_data(deposit_amount=amount, exchange_rate_value=exchange_rate)
        if selected_method == texts['btc'][user_language]:
            await state.set_state(BalanceStates.waiting_for_btc_confirmation)
        else:
            await state.set_state(BalanceStates.waiting_for_usdt_confirmation)
        await message.answer(confirmation_message, reply_markup=ReplyKeyboardRemove())
# Функция для проверки транзакции через TronScan API
async def check_usdt_transaction(tx_hash: str, language: str):
    tron_api_url = f"https://api.tronscan.org/api/transaction/{tx_hash}"
    response = requests.get(tron_api_url)

    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            tx_data = data["data"][0]
            received_amount = float(tx_data['amount']) / 10 ** 6  # Преобразуем в USDT
            return received_amount
        else:
            return texts['transaction_data_missing'][language]
    else:
        return texts['transaction_check_failed'][language]

# Проверка транзакции для BTC через BscScan API
async def check_btc_transaction(tx_hash: str, language: str):
    bsc_api_url = f"https://api.bscscan.com/api?module=transaction&action=gettxreceiptstatus&txhash={tx_hash}&apikey=YourApiKeyToken"
    response = requests.get(bsc_api_url)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "1":
            return True  # Успешная транзакция
        else:
            return texts['transaction_failed'][language]
    return texts['transaction_check_failed'][language]
# Подтверждение пополнения для BTC
@router.message(BalanceStates.waiting_for_btc_confirmation)
async def confirm_btc_deposit(message: Message, state: FSMContext):
    tx_hash = message.text.strip()
    language = get_user_language(message.from_user.id)
    is_valid = await check_btc_transaction(tx_hash, language)

    if is_valid:
        user_data = await state.get_data()
        deposit_amount = user_data.get("deposit_amount")
        user_id = message.from_user.id
        await update_balance(user_id, deposit_amount)

        # Отправка сообщения пользователю
        await message.answer(texts['btc_deposit_success'][language].format(amount=deposit_amount))

        # Уведомление администратора
        admin_message = texts['btc_admin_notification'][language].format(
            username=message.from_user.username,
            user_id=user_id,
            amount=deposit_amount,
            tx_hash=tx_hash
        )
        admins = get_admins()  # Предполагается, что функция возвращает список ID администраторов
        for admin in admins:
            await message.bot.send_message(chat_id=admin, text=admin_message)
    else:
        await message.answer(texts['transaction_not_found'][language])

    await state.clear()

# Обработчик для подтверждения пополнения через USDT
@router.message(BalanceStates.waiting_for_usdt_confirmation)
async def confirm_deposit(message: Message, state: FSMContext):
    tx_hash = message.text.strip()  # Получаем хэш транзакции от пользователя
    language = get_user_language(message.from_user.id)
    received_amount = await check_usdt_transaction(tx_hash, language)

    if received_amount is None:
        await message.answer(texts['transaction_not_found'][language])
    else:
        user_data = await state.get_data()
        deposit_amount = user_data.get("deposit_amount")
        user_id = message.from_user.id

        if received_amount >= deposit_amount:
            # Обновление баланса пользователя
            await update_balance(user_id, deposit_amount)

            # Уведомление пользователя
            await message.answer(texts['usdt_deposit_success'][language].format(amount=deposit_amount))

            # Уведомление администраторов через get_admins
            admin_message = texts['usdt_admin_notification'][language].format(
                username=message.from_user.username,
                user_id=user_id,
                amount=deposit_amount,
                tx_hash=tx_hash
            )
            admins = get_admins()  # Предполагается, что функция возвращает список ID администраторов
            for admin in admins:
                await message.bot.send_message(chat_id=admin, text=admin_message)
        else:
            await message.answer(texts['transaction_amount_too_low'][language])

    await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['transfer_funds_button'].get(lang, '') or '').strip() for lang in texts['transfer_funds_button']})
async def start_transfer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_language = (await state.get_data()).get('language', 'ru')

    logging.debug(f"ID пользователя: {user_id}, Язык: {user_language}")

    expected_text = texts['transfer_funds_button'][user_language]
    received_text = message.text.strip()

    if received_text == expected_text:
        logging.debug(f"Сообщение соответствует кнопке '{expected_text}'")
        send_message = texts['enter_username'][user_language]

        try:
            await message.answer(send_message, reply_markup=cancel_keyboard())  # Добавляем клавиатуру с кнопкой "Отмена"
            logging.debug("Сообщение с запросом имени пользователя успешно отправлено.")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения: {e}")
            return

        await state.set_state(TransferState.waiting_for_username)
        logging.debug("Состояние установлено: TransferState.waiting_for_username")
    else:
        logging.warning(f"Сообщение не соответствует ожидаемому тексту кнопки. Получено: '{received_text}', ожидаемо: '{expected_text}'")
@router.message(TransferState.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    username_or_id = message.text.strip()
    logging.debug(f"Пользователь @{message.from_user.username} ввёл username или ID получателя: {username_or_id}")
    user_id = message.from_user.id
    user_language = (await state.get_data()).get('language', 'ru')

    try:
        if username_or_id.isdigit():
            recipient_user_id = int(username_or_id)
            balance = await get_user_balance_perevod_by_id(recipient_user_id)
            if balance is None:
                raise ValueError(f"Пользователь с ID {recipient_user_id} не найден.")
            username = await get_username_by_id(recipient_user_id)
            logging.debug(f"Пользователь найден по ID {recipient_user_id}: @{username}")
        else:
            balance = await get_user_balance_perevod(username_or_id)
            if balance is None:
                raise ValueError(f"Пользователь @{username_or_id} не найден.")
            username = username_or_id
            logging.debug(f"Пользователь найден по username: @{username}")
    except ValueError as e:
        logging.warning(f"Ошибка: {e}")
        user_language = (await state.get_data()).get('language', 'ru')
        await message.answer(texts['user_not_found'][user_language], reply_markup=cancel_keyboard())  # Добавляем кнопку "Отмена"
        await state.clear()
        return

    await state.update_data(username=username)
    logging.debug(f"Процесс перевода продолжен для получателя @{username}.")
    await message.answer(texts['enter_amount'][user_language], reply_markup=cancel_keyboard())  # Добавляем кнопку "Отмена"
    await state.set_state(TransferState.waiting_for_amount)


@router.message(TransferState.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля.")
    except ValueError as e:
        logging.warning(f"Некорректная сумма: {e}")
        user_language = (await state.get_data()).get('language', 'ru')
        await message.answer(texts['enter_valid_amount'][user_language],
                             reply_markup=cancel_keyboard())  # Добавляем кнопку "Отмена"
        return

    data = await state.get_data()
    recipient_username = data["username"]
    sender_username = message.from_user.username

    try:
        sender_balance = float(await get_user_balance_perevod(sender_username))
        if sender_balance < amount:
            raise ValueError(f"Недостаточно средств. Баланс: {sender_balance}, требуется: {amount}")
    except ValueError as e:
        logging.warning(f"Ошибка: {e}")
        user_language = (await state.get_data()).get('language', 'ru')
        await message.answer(texts['insufficient_funds'][user_language],
                             reply_markup=cancel_keyboard())  # Добавляем кнопку "Отмена"
        await state.clear()
        return

    try:
        await update_user_balance_perevod(sender_username, -amount)
        await update_user_balance_perevod(recipient_username, amount)
        logging.debug(f"Успешный перевод {amount} от @{sender_username} к @{recipient_username}.")
    except Exception as e:
        logging.error(f"Ошибка при выполнении перевода: {e}")
        user_language = (await state.get_data()).get('language', 'ru')
        await message.answer(texts['transfer_failed'][user_language],
                             reply_markup=cancel_keyboard())  # Добавляем кнопку "Отмена"
        await state.clear()
        return

    user_language = (await state.get_data()).get('language', 'ru')
    transfer_success_text = texts['transfer_success'][user_language].format(amount=amount, recipient=recipient_username)
    await message.answer(transfer_success_text)  # Добавляем кнопку "Отмена"

    # Уведомление получателя
    try:
        received_transfer_text = texts['received_transfer'][user_language].format(amount=amount,
                                                                                  sender_username=sender_username)

        recipient_chat_id = await get_user_for_perevod(recipient_username)
        await message.bot.send_message(chat_id=recipient_chat_id, text=received_transfer_text)

    except Exception as e:
        logging.error(f"Ошибка при уведомлении получателя @{recipient_chat_id}: {e}")

    await state.clear()


