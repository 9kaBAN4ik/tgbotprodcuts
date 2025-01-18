from aiogram.filters import Command  # Импортируем Command для работы с фильтром команд
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import is_partner, add_product_to_db, get_all_products, get_product_by_code
from config import DEFAULT_LANGUAGE

router = Router()


# Шаги состояния для добавления продукта
class AddProductForm(StatesGroup):
    name = State()  # Название продукта
    description = State()  # Описание продукта
    price = State()  # Цена продукта


@router.message(Command(commands=["add_product"]))
async def start_add_product(message: Message, state: FSMContext):
    # Получаем текущий язык пользователя из состояния
    user_data = await state.get_data()
    user_language = user_data.get('language', DEFAULT_LANGUAGE)

    # Выбираем сообщение в зависимости от языка
    if not await is_partner(message.from_user.id):
        response = "Only partners can add products." if user_language == "en" else "Только партнёры могут добавлять продукты."
        await message.answer(response)
        return

    prompt = "Please enter the product name:" if user_language == "en" else "Введите название продукта:"
    await message.answer(prompt)
    await state.set_state(AddProductForm.name)


@router.message(AddProductForm.name)
async def add_product_name(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_language = user_data.get('language', DEFAULT_LANGUAGE)

    await state.update_data(name=message.text)
    prompt = "Please enter the product description:" if user_language == "en" else "Введите описание продукта:"
    await message.answer(prompt)
    await state.set_state(AddProductForm.description)


@router.message(AddProductForm.description)
async def add_product_description(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_language = user_data.get('language', DEFAULT_LANGUAGE)

    await state.update_data(description=message.text)
    prompt = "Please enter the product price (in VED):" if user_language == "en" else "Введите цену продукта (в VED):"
    await message.answer(prompt)
    await state.set_state(AddProductForm.price)


@router.message(AddProductForm.price)
async def add_product_price(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_language = user_data.get('language', DEFAULT_LANGUAGE)

    try:
        # Преобразуем цену в float
        price = float(message.text)
        data = await state.get_data()

        # Проверяем, что все поля заполнены
        if not data.get("name") or not data.get("description"):
            response = "Product name and description must be filled." if user_language == "en" else "Название и описание продукта должны быть заполнены."
            await message.answer(response)
            return

        # Добавляем продукт в базу данных
        await add_product_to_db(
            name=data["name"],
            description=data["description"],
            price=price,
            partner_id=message.from_user.id
        )

        response = "Product successfully added!" if user_language == "en" else "Продукт успешно добавлен!"
        await message.answer(response)
        await state.clear()  # Очищаем состояние после завершения

    except ValueError:
        response = "Price must be a number. Please enter it again." if user_language == "en" else "Цена должна быть числом. Пожалуйста, введите снова."
        await message.answer(response)
@router.message(Command(commands=["products"]))
async def list_products(message: Message):
    products = await get_all_products()  # Функция для получения всех продуктов из базы данных
    response = "📋 Список продуктов:\n"
    for product in products:
        # Замыливаем индивидуальные продукты
        name = product["name"] if not product.get("is_personal") else "Продукт доступен по коду"
        response += f"🔹 {name} — {product['price']} VED\n"
    response += "\nВведите код, чтобы посмотреть индивидуальный продукт, или выберите из списка."
    await message.answer(response)

@router.message()
async def get_product_info(message: Message):
    product_code = message.text.strip()
    product = await get_product_by_code(product_code)  # Функция для поиска продукта по коду
    if product:
        text = (
            f"🛒 Название: {product['name']}\n"
            f"📄 Описание: {product['description']}\n"
            f"💰 Цена: {product['price']} VED\n"
        )
        # Добавляем кнопку "Оплатить"
        keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Оплатить", callback_data=f"buy:{product['id']}"))
        await message.answer_photo(product["image"], caption=text, reply_markup=keyboard)
    else:
        await message.answer("❌ Продукт с таким кодом не найден.")