import sqlite3
from config import DB_PATH
from datetime import datetime
import time
import aiosqlite
import json
import logging
from typing import Optional, Dict, List
# Функция для подключения к базе данных
def connect_db():
    return sqlite3.connect(DB_PATH)


def initialize_db():
    with connect_db() as conn:
        cursor = conn.cursor()

        # Создание таблицы пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'en',
            balance REAL DEFAULT 0,
            referral_link TEXT,
            role TEXT DEFAULT 'user'  -- Добавляем новый столбец для роли
        )
        """)
        # Создание таблицы продуктов (с добавлением столбца partner_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                is_subscription INTEGER NOT NULL,
                subscription_period TEXT,
                partner_id INTEGER NOT NULL,
                image TEXT,
                product_type TEXT,
                category TEXT,  -- Тип продукта (например, "Корпоративный ретрит", "Онлайн-сессия")
                code TEXT UNIQUE,  -- Уникальный код продукта
                is_hidden INTEGER DEFAULT 0,  -- Признак, скрыт ли продукт (0 - не скрыт, 1 - скрыт)
                after_purchase TEXT,
                course_id INTEGER,
                status TEXT DEFAULT 'pending'
            )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT UNIQUE NOT NULL,
        product_count INTEGER DEFAULT 0
    )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                purchase_date TEXT DEFAULT CURRENT_TIMESTAMP,
                course_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            """)

        # Таблица для хранения информации о рефералах
        cursor.execute("""
               CREATE TABLE IF NOT EXISTS referrals (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   referrer_id INTEGER,  -- ID пользователя, который пригласил
                   referred_id INTEGER,  -- ID приглашённого пользователя
                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
               )
               """)
        # Таблица для курсов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL DEFAULT 0,
                partner_id INTEGER,
                unique_id TEXT UNIQUE
            )
        """)

        # Таблица для уроков
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    title TEXT,
                    description TEXT,
                    material_link TEXT,
                    FOREIGN KEY(course_id) REFERENCES courses(id)
                )
                """)

        # Таблица для вопросов
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id INTEGER,
                    text TEXT,
                    options TEXT,
                    correct_answer INTEGER,
                    FOREIGN KEY(lesson_id) REFERENCES lessons(id)
                )
                """)
        # Таблица для отслеживания прогресса пользователя
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,       -- Идентификатор пользователя
                current_question_id INTEGER,       -- ID текущего вопроса
                product_id INTEGER,
                completed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (current_question_id) REFERENCES questions(id),  -- Внешний ключ на таблицу вопросов
                FOREIGN KEY (product_id) REFERENCES products(id)
                    )
                    """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                credo TEXT NOT NULL,
                logo_url TEXT,
                show_in_list BOOLEAN DEFAULT TRUE,
                partner_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS aphorisms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    author TEXT NOT NULL
                )
            ''')
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS aphorism_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL
                )
            ''')
        cursor.execute('''
               CREATE TABLE IF NOT EXISTS exchange_rates (
                currency TEXT PRIMARY KEY,
                rate TEXT
            )
           ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_tags(
             id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tag_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                UNIQUE (user_id, tag),
                FOREIGN KEY (tag) REFERENCES product_tags(tag)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Идентификатор награды
            referral_system_id INTEGER,  -- Ссылка на реферальную систему
            level INTEGER NOT NULL,  -- Уровень
            reward_type TEXT NOT NULL,  -- Тип награды: "registration", "top_up", "purchase"
            amount INTEGER NOT NULL,  -- Размер награды
            FOREIGN KEY (referral_system_id) REFERENCES referral_system(id)  -- Связь с таблицей реферальной системы
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_system (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Идентификатор настройки реферальной системы
            levels INTEGER NOT NULL  -- Количество уровней в реферальной системе
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS partner_questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,           -- ID пользователя, задавшего вопрос
            partner_id INTEGER NOT NULL,        -- ID партнёра (по сути chat_id)
            product_id INTEGER NOT NULL,        -- ID продукта
            question_id INTEGER NOT NULL,       -- ID вопроса
            question_text TEXT NOT NULL,        -- Текст вопроса
            user_message TEXT NOT NULL,         -- Сообщение пользователя
            status TEXT NOT NULL DEFAULT 'new', -- Статус вопроса: 'new', 'answered'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ticket_price INTEGER,
                fund INTEGER,
                active INTEGER DEFAULT 0
            )
            ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_id INTEGER,
                user_id INTEGER,
                username TEXT,
                ticket_number INTEGER,
                is_winner INTEGER DEFAULT 0,
                prize TEXT,
                FOREIGN KEY (lottery_id) REFERENCES lottery (id)
            )
            ''')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedbacks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    feedback_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()



# Функция для добавления пользователя в базу данных, если его ещё нет
async def add_user(user_id: int, username: str, first_name: str):
    conn = connect_db()
    cursor = conn.cursor()

    # Проверка, существует ли уже пользователь в базе данных
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("""
        INSERT INTO users (user_id, username, first_name, role)
        VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, "user"))  # Устанавливаем роль по умолчанию
        conn.commit()
    conn.close()


def add_partner(name: str, credo: str, logo_file_id: str, show_in_list: bool, partner_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    # Убедитесь, что данные передаются в нужном порядке:
    cursor.execute("""
        INSERT INTO partners (name, credo, logo_url, show_in_list, partner_id)
        VALUES (?, ?, ?, ?, ?)
    """, (name, credo, logo_file_id, show_in_list, partner_id))
    conn.commit()


def get_visible_partners():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, credo, logo_url, status,partner_id
        FROM partners
        WHERE show_in_list = 1 AND status = 'approved'
    """)
    return cursor.fetchall()


# Функция для установки роли пользователя
async def set_user_role(user_id: int, role: str):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    conn.commit()
    conn.close()


# Функция для получения роли пользователя
async def get_user_role(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


async def get_user_for_perevod(recipient_username):
    conn = connect_db()
    cursor = conn.cursor()
    username_lower = recipient_username.lower()  # Приведение к нижнему регистру
    logger.info(f"Запрос к базе данных для пользователя с username: {recipient_username}")

    # Используем LOWER для приведения username в базе данных к нижнему регистру
    cursor.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (username_lower,))

    row = cursor.fetchone()
    if row:
        logger.info(f"Найден user_id: {row[0]} для username: {recipient_username}")
    else:
        logger.warning(f"Пользователь с username: {recipient_username} не найден.")

    conn.close()

    return row[0] if row else None

async def get_username_by_id(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id =?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]
    return None


async def get_user_balance_perevod_by_id(recipient_user_id):
    conn = connect_db()
    cursor = conn.cursor()
    user_id = recipient_user_id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        balance = row[0]
        if balance is None:
            logger.warning(f"Пользователь с user_id {user_id} имеет пустой баланс.")
            return None
        logger.info(f"Найден user с балансом {balance} для user_id:{user_id}")
        return balance
    else:
        logger.warning(f"Пользователь с user_id {user_id} не найден.")
        return None


async def is_partner(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0] == "partner"
async def is_admin(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0] == "admin"
# Получение баланса пользователя
async def get_user_balance(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]  # Возвращаем баланс
    else:
        return 0  # Если пользователь не найден, возвращаем 0

def get_course_by_id(course_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, description, price
        FROM courses 
        WHERE id = ?
    """, (course_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "price": row[3],  # Убедитесь, что поле 'price' существует
        }
    return None



async def process_payment(user_id: int, product_id: int) -> bool:
    """
    Проверяет баланс пользователя, списывает стоимость продукта и возвращает статус оплаты.
    :param user_id: ID пользователя
    :param product_id: ID продукта
    :return: True, если оплата прошла успешно, иначе False
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Получаем баланс пользователя
        user_balance = await get_user_balance(user_id)

        # Получаем стоимость продукта
        cursor.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return False  # Продукт не найден
        product_price = product[0]

        # Проверяем, достаточно ли средств на балансе
        if user_balance < product_price:
            return False  # Недостаточно средств

        # Списываем стоимость продукта с баланса пользователя
        new_balance = user_balance - product_price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

        # Фиксируем покупку в таблице `purchases`
        cursor.execute("""
        INSERT INTO purchases (user_id, product_id)
        VALUES (?, ?)
        """, (user_id, product_id))

        conn.commit()
        return True  # Оплата прошла успешно

    except Exception as e:
        print(f"Ошибка при обработке оплаты: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()

async def get_user_referral_link(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Проверяем, есть ли пользователь в базе данных
        cursor.execute("SELECT referral_link FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result and result[0]:
            # Если ссылка уже существует, возвращаем её
            return result[0]

        # Если ссылки нет, проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()

        if not user_exists:
            # Если пользователь отсутствует, выбрасываем исключение или обрабатываем это явно
            raise ValueError("Пользователь не найден в базе данных. Сначала зарегистрируйтесь через /start.")

        # Создаём новую реферальную ссылку
        referral_link = f"https://t.me/botkworktest_bot?start=ref{user_id}"
        cursor.execute(
            "UPDATE users SET referral_link = ? WHERE user_id = ?",
            (referral_link, user_id),
        )
        conn.commit()

        return referral_link

async def get_courses_by_partner(partner_id: int) -> list[dict]:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name FROM courses WHERE partner_id = ?
    """, (partner_id,))
    courses = cursor.fetchall()
    conn.close()

    # Возвращаем курсы в виде списка словарей
    return [{"id": course[0], "name": course[1]} for course in courses]

async def is_user_partner(user_id: int) -> bool:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 'partner'
# Получение списка продуктов
async def get_product_list():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products")
    products = cursor.fetchall()
    conn.close()
    return [{"name": product[0], "price": product[1]} for product in products]

async def is_user_partner(user_id: int) -> bool:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_partner FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 1 if result else False

# Функция для добавления нового продукта
async def add_product_to_db(
        name: str,
        description: str,
        price: float,
        product_type: str = None,  # Принимаем product_type
        is_subscription: bool = False,
        partner_id: int = None,
        image: str = None,
        subscription_period: int = None,
        category: str = None,
        code: str = None,
        is_hidden: bool = False,
        after_purchase: str = None,
        course_id: int = None,
        tags: list = []  # Список тегов
):
    conn = connect_db()
    cursor = conn.cursor()

    # Обработка product_type: разбиваем строку на отдельные типы
    product_type_list = [ptype.strip() for ptype in product_type.split(',')] if product_type else []

    product_type_ids = []

    for ptype in product_type_list:
        # Проверяем, существует ли текущий product_type в таблице product_types
        cursor.execute('''
            SELECT id, product_count FROM product_types WHERE type = ?
        ''', (ptype,))
        result = cursor.fetchone()

        if result is None:
            # Если тип не найден, добавляем его с начальным счётчиком
            cursor.execute('''
                INSERT INTO product_types (type, product_count) VALUES (?, ?)
            ''', (ptype, 1))
            product_type_ids.append(cursor.lastrowid)  # Сохраняем id нового типа
        else:
            # Если тип найден, увеличиваем счётчик
            product_type_id = result[0]
            product_type_ids.append(product_type_id)
            cursor.execute('''
                UPDATE product_types SET product_count = product_count + 1 WHERE id = ?
            ''', (product_type_id,))

    # Вставка данных в таблицу products, используя первый из product_type_ids
    # (или None, если список пуст)
    cursor.execute(''' 
        INSERT INTO products (
            name, description, price, product_type, is_subscription, partner_id, image, 
            subscription_period, category, code, is_hidden, after_purchase, course_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name, description, price, product_type,
        is_subscription, partner_id, image, subscription_period, category, code,
        is_hidden, after_purchase, course_id
    ))

    # Получаем ID последнего добавленного продукта
    product_id = cursor.lastrowid

    # Вставка тегов в таблицу product_tags
    for tag in tags:
        cursor.execute(''' 
            INSERT INTO product_tags (product_id, tag)
            VALUES (?, ?)
        ''', (product_id, tag))

    conn.commit()
    conn.close()







async def purchase_product(user_id: int, price: float) -> bool:
    conn = connect_db()
    cursor = conn.cursor()

    # Проверяем, хватает ли баланса у пользователя
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result and result[0] >= price:
        # Обновляем баланс
        new_balance = result[0] - price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()
        conn.close()
        return True  # Покупка успешна
    else:
        conn.close()
        return False  # Недостаточно средств


async def add_course(name: str, description: str, partner_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    # Проверяем, существует ли курс с таким же названием и partner_id
    cursor.execute("""
    SELECT id FROM courses WHERE name = ? AND partner_id = ?
    """, (name, partner_id))

    existing_course = cursor.fetchone()

    if existing_course:
        # Если курс уже существует, возвращаем его ID
        print(f"Курс с таким именем уже существует: ID = {existing_course[0]}")
        conn.close()
        return existing_course[0]  # Возвращаем ID существующего курса

    # Если курс не найден, добавляем новый
    cursor.execute("""
    INSERT INTO courses (name, description, partner_id) 
    VALUES (?, ?, ?)
    """, (name, description, partner_id))

    conn.commit()

    # Получаем курс ID сразу после добавления
    cursor.execute("SELECT last_insert_rowid()")
    course_id = cursor.fetchone()[0]

    conn.close()

    print(f"Добавлен курс с ID: {course_id}")  # Логирование
    return course_id




async def get_courses_for_partner(partner_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM courses WHERE partner_id = ?", (partner_id,))
    courses = cursor.fetchall()
    conn.close()
    return [{"id": course[0], "title": course[1], "description": course[2]} for course in courses]


async def get_course_by_id(course_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()
    conn.close()
    if not course:
        raise ValueError(f"Курс с ID {course_id} не найден.")
    return {"id": course[0], "name": course[1], "description": course[2]}


async def get_all_courses():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM courses")
    courses = cursor.fetchall()
    conn.close()
    return [{"id": course[0], "name": course[1], "description": course[2]} for course in courses]

async def add_lesson(course_id: int, title: str, description: str, material_link: str = None):
    conn = sqlite3.connect(DB_PATH)  # Замените на ваш путь к базе данных
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO lessons (course_id, title, description, material_link)
    VALUES (?, ?, ?, ?)
    """, (course_id, title, description, material_link))

    conn.commit()

    # Получаем ID последней вставленной строки
    lesson_id = cursor.lastrowid

    conn.close()

    return lesson_id


async def get_lesson_by_id(lesson_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, material_link FROM lessons WHERE id = ?", (lesson_id,))
    lesson = cursor.fetchone()
    conn.close()
    return {"id": lesson[0], "title": lesson[1], "description": lesson[2], "material_link": lesson[3]} if lesson else None

async def get_lessons_for_course(course_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM lessons WHERE course_id = ?", (course_id,))
    lessons = cursor.fetchall()
    conn.close()
    return [{"id": lesson[0], "title": lesson[1], "description": lesson[2]} for lesson in lessons]



async def add_question(question_text: str, options: list, correct_answer: int, lesson_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    # Преобразуем список options в строку
    options_str = json.dumps(options)  # Преобразуем список в строку

    # Выполняем запрос с преобразованным параметром options_str
    cursor.execute("""
        INSERT INTO questions (text, options, correct_answer, lesson_id) 
        VALUES (?, ?, ?, ?)
    """, (question_text, options_str, correct_answer, lesson_id))

    conn.commit()
    conn.close()



async def get_questions_for_lesson(lesson_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, options, correct_answer FROM questions WHERE lesson_id = ?", (lesson_id,))
    questions = cursor.fetchall()
    conn.close()
    return [{"id": question[0], "text": question[1], "options": question[2], "correct_answer": question[3]} for question in questions]

async def get_partner_for_course(course_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM partners WHERE course_id = ?", (course_id,))
    partner = cursor.fetchone()
    conn.close()
    return partner[0] if partner else None


async def get_questions_for_partner(partner_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    query = """
    SELECT q.text, q.options
    FROM questions q
    JOIN lessons l ON q.lesson_id = l.id
    JOIN courses c ON l.course_id = c.id
    WHERE c.partner_id = ?
    """

    cursor.execute(query, (partner_id,))
    questions = cursor.fetchall()

    conn.close()

    question_list = []
    for question in questions:
        question_list.append({
            "text": question[0],
            "options": question[1]
        })

    return question_list

async def update_course_tags(course_id: int, tags: list[str]):
    conn = connect_db()
    cursor = conn.cursor()
    tags_str = ",".join(tags)
    cursor.execute("UPDATE courses SET tags = ? WHERE id = ?", (tags_str, course_id))
    conn.commit()
    conn.close()

async def get_courses_by_tag(tag: str):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM courses WHERE tags LIKE ?", (f"%{tag}%",))
    courses = cursor.fetchall()
    conn.close()
    return [{"id": course[0], "title": course[1]} for course in courses]


def get_user_progress(user_id):
    """Получить прогресс пользователя по его ID, включая current_question_id и lesson_id."""
    connection = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
    cursor = connection.cursor()

    cursor.execute("SELECT current_question_id, lesson_id,product_id FROM user_progress WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    connection.close()

    if result:
        return {
            "user_id": user_id,
            "current_question_id": result[0],
            "lesson_id": result[1], # Добавляем lesson_id в результат
            "product_id": result[2]
        }
    return None



def update_user_progress(user_id, next_question_id, product_id, lesson_id):
    """Обновить прогресс пользователя (перейти к следующему вопросу) с учётом product_id и lesson_id."""
    connection = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
    cursor = connection.cursor()

    # Обновляем прогресс пользователя, если он уже существует, обновляем current_question_id, product_id и lesson_id
    cursor.execute("""
        INSERT INTO user_progress (user_id, current_question_id, product_id, lesson_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET current_question_id = ?, product_id = ?, lesson_id = ?
    """, (user_id, next_question_id, product_id, lesson_id, next_question_id, product_id, lesson_id))

    connection.commit()
    connection.close()

def create_user_progress(user_id, product_id, lesson_id=1):
    """Создает новый прогресс для пользователя, включая продукт и урок."""
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Вставляем новый прогресс для пользователя с product_id и lesson_id
    cursor.execute("""
        INSERT INTO user_progress (user_id, current_question_id, completed, product_id, lesson_id)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, 1, False, product_id, lesson_id))  # Инициализируем с вопросом 1 и статусом "не завершено"

    connection.commit()
    connection.close()



def get_questions_by_lesson(lesson_id):
    """Получить все вопросы для урока по ID."""
    conn = sqlite3.connect(DB_PATH)  # Замените на путь к вашей базе данных
    cursor = conn.cursor()

    # Запрос для получения всех вопросов для урока, отсортированных по id
    cursor.execute("SELECT * FROM questions WHERE lesson_id = ? ORDER BY id", (lesson_id,))

    # Извлекаем все вопросы
    questions = cursor.fetchall()

    # Закрываем соединение
    conn.close()

    # Возвращаем вопросы в виде списка словарей для удобства работы
    return [{'id': row[0], 'lesson_id': row[1], 'text': row[2], 'options': row[3].split(','),
             'correct_answer': row[4]} for row in questions]


def get_next_question_in_lesson(lesson_id, current_question_id):
    """Получить следующий вопрос для урока."""
    # Получаем все вопросы для урока
    questions = get_questions_by_lesson(lesson_id)

    print(f"Вопросы для урока {lesson_id}: {questions}")  # Логируем вопросы

    # Ищем индекс текущего вопроса
    current_index = next((index for index, q in enumerate(questions) if q['id'] == current_question_id), None)

    print(f"Текущий вопрос: {current_question_id}, индекс: {current_index}")  # Логируем индекс текущего вопроса

    # Если текущий вопрос не найден или это последний вопрос
    if current_index is None or current_index + 1 >= len(questions):
        print("Следующего вопроса нет!")  # Логируем отсутствие следующего вопроса
        return None  # Нет следующего вопроса

    # Возвращаем следующий вопрос
    next_question = questions[current_index + 1]
    print(f"Следующий вопрос: {next_question}")  # Логируем следующий вопрос
    return next_question


def get_next_question_id(current_question_id):
    """Получить ID следующего вопроса."""
    connection = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id FROM questions WHERE id > ? ORDER BY id ASC LIMIT 1
    """, (current_question_id,))
    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]
    return None  # Если вопросов больше нет, возвращаем None


async def delete_course(course_id):
    await db_execute("DELETE FROM courses WHERE id = ?", (course_id,))
    await db_execute("DELETE FROM lessons WHERE course_id = ?", (course_id,))

async def update_lesson_title(lesson_id, new_title):
    query = "UPDATE lessons SET title = ? WHERE id = ?"
    await db_execute(query, (new_title, lesson_id))

async def get_user_for_question(question_id):
    query = "SELECT user_id FROM questions WHERE id = ?"
    result = await db_fetchone(query, (question_id,))
    return result['user_id'] if result else None


def get_course_by_code(course_code):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, description, partner_id, unique_id, price 
            FROM courses 
            WHERE unique_id = ?
        """, (course_code,))
        row = cursor.fetchone()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "partner_id": row[3],
            "unique_id": row[4],
            "price": row[5],
        }
    return None


def get_all_courses():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, description, partner_id, unique_id, price 
            FROM courses
        """)
        rows = cursor.fetchall()

    courses = []
    for row in rows:
        courses.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "partner_id": row[3],
            "unique_id": row[4],
            "price": row[5],
        })
    return courses


def mark_lesson_as_completed(user_id, lesson_id):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_progress (user_id, lesson_id, completed, completion_date)
        VALUES (?, ?, TRUE, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, lesson_id) 
        DO UPDATE SET completed = TRUE, completion_date = CURRENT_TIMESTAMP
        """, (user_id, lesson_id))
        conn.commit()

async def get_completed_lessons(user_id, course_id):
    # Получить количество завершённых уроков для данного пользователя и курса
    completed_lessons = await db.fetch_all(
        "SELECT COUNT(*) FROM lesson_progress WHERE user_id = ? AND course_id = ? AND is_completed = TRUE",
        user_id, course_id
    )
    return completed_lessons[0][0] if completed_lessons else 0

async def get_completed_questions(user_id, course_id):
    # Получить количество завершённых вопросов для данного пользователя и курса
    completed_questions = await db.fetch_all(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND course_id = ? AND is_completed = TRUE",
        user_id, course_id
    )
    return completed_questions[0][0] if completed_questions else 0

async def update_question_progress(user_id, course_id, lesson_id, question_id, is_completed):
    await db.execute(
        "INSERT INTO user_progress (user_id, course_id, lesson_id, question_id, is_completed) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, course_id, lesson_id, question_id) "
        "DO UPDATE SET is_completed = ?",
        user_id, course_id, lesson_id, question_id, is_completed, is_completed
    )
async def update_lesson_progress(user_id, course_id, lesson_id, is_completed):
    await db.execute(
        "INSERT INTO lesson_progress (user_id, course_id, lesson_id, is_completed) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, course_id, lesson_id) "
        "DO UPDATE SET is_completed = ?",
        user_id, course_id, lesson_id, is_completed, is_completed
    )
async def check_course_completion(user_id, course_id):
    completed_lessons = await get_completed_lessons(user_id, course_id)
    total_lessons = len(await get_lessons_for_course(course_id))  # Получаем все уроки курса

    if completed_lessons == total_lessons:
        await notify_user_course_completed(user_id, course_id)

async def get_referral_count(user_id: int) -> int:
    """Получает количество приглашённых пользователей."""
    query = """
    SELECT COUNT(*) FROM referrals
    WHERE referrer_id = ?
    """
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    count = cursor.fetchone()[0]
    return count

def get_user_earnings(user_id: int) -> int:
    """
    Получить заработок пользователя на основе приглашённых рефералов.
    :param user_id: ID пользователя
    :return: Заработанные бонусы
    """
    query = """
    SELECT COUNT(*) 
    FROM referrals 
    WHERE referrer_id = ?
    """
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    referral_count = result[0] if result else 0  # Если результата нет, то 0
    cursor.close()
    conn.close()

    # Каждый приглашённый приносит 10 Ved
    earnings = referral_count * 10
    return earnings
def get_product_by_id(product_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Возвращаем строки как словари
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, description, price, image, product_type, category, code, after_purchase, is_subscription, subscription_period
        FROM products 
        WHERE id = ?
    """, (product_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        product = dict(row)  # Конвертируем результат в словарь
        product["is_subscription"] = bool(product["is_subscription"])  # Преобразуем флаг в bool
        # Удаляем subscription_period, если это не подписка
        if not product["is_subscription"]:
            product.pop("subscription_period", None)
        return product
    return None


# Функция для получения продукта по коду (с учетом скрытия)
def get_product_by_code(code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            id, 
            name, 
            description, 
            price, 
            image, 
            type, 
            is_hidden, 
            status, 
            is_subscription, 
            subscription_period, 
            category
        FROM products 
        WHERE code = ?
    """, (code,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "type": row[5],
            "is_hidden": bool(row[6]),
            "status": row[7],
            "is_subscription": bool(row[8]),
            "subscription_period": row[9],
            "category": row[10]
        }
    return None



# Функция для получения всех видимых продуктов (где is_hidden = 0)
def get_visible_products():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, image, type FROM products WHERE is_hidden = 0")
    rows = cursor.fetchall()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "type": row[5]
        })
    return products

# Функция для получения всех продуктов, включая скрытые (по коду)
def get_all_products():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            id, 
            name, 
            description, 
            price, 
            image, 
            product_type, 
            is_hidden, 
            status,
            is_subscription,
            subscription_period,
            category,
            partner_id
        FROM products
    """)
    rows = cursor.fetchall()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "product_type": row[5],
            "is_hidden": bool(row[6]),
            "status": row[7],
            "is_subscription": bool(row[8]),  # Добавили флаг подписки
            "subscription_period": row[9],   # Добавили период подписки
            "category": row[10],
            "partner_id":row[11 ]# Добавили категорию
        })
    return products



def mark_product_as_purchased(user_id, product_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO purchases (user_id, product_id)
    VALUES (?, ?)
    """, (user_id, product_id))
    conn.commit()
    conn.close()

async def purchase_course(user_id: int, product_id: int):
    with connect_db() as conn:
        cursor = conn.cursor()

        # Проверяем наличие продукта
        cursor.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return "Продукт не найден."

        price = product[0]

        # Проверяем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return "Пользователь не найден."

        balance = user[0]
        if balance < price:
            return "Недостаточно средств для покупки."

        # Списываем сумму с баланса
        new_balance = balance - price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

        # Добавляем покупку
        cursor.execute("INSERT INTO purchases (user_id, product_id) VALUES (?, ?)", (user_id, product_id))

        # Получаем курс, связанный с продуктом
        cursor.execute("SELECT id FROM courses WHERE id = ?", (product_id,))
        course = cursor.fetchone()
        if not course:
            return "Курс не найден, но покупка зарегистрирована."

        conn.commit()
        return f"Покупка успешно завершена. Вы получили доступ к курсу с ID {course[0]}."


async def get_next_lesson(user_id: int, course_id: int):
    with connect_db() as conn:
        cursor = conn.cursor()

        # Проверяем, куплен ли курс
        cursor.execute("""
            SELECT 1 FROM purchases
            WHERE user_id = ? AND product_id = ?
        """, (user_id, course_id))
        if not cursor.fetchone():
            return "У вас нет доступа к этому курсу."

        # Ищем первый незавершённый урок
        cursor.execute("""
            SELECT l.id, l.title, l.description, l.material_link
            FROM lessons l
            LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = ?
            WHERE l.course_id = ? AND (up.completed IS NULL OR up.completed = 0)
            ORDER BY l.id LIMIT 1
        """, (user_id, course_id))
        lesson = cursor.fetchone()
        if not lesson:
            return "Все уроки курса завершены."

        lesson_id, title, description, material_link = lesson
        return f"Следующий урок:\n{title}\n{description}\nМатериалы: {material_link}"
async def complete_lesson(user_id: int, lesson_id: int):
    with connect_db() as conn:
        cursor = conn.cursor()

        # Проверяем, существует ли урок
        cursor.execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,))
        if not cursor.fetchone():
            return "Урок не найден."

        # Проверяем, завершал ли пользователь этот урок
        cursor.execute("""
            SELECT completed FROM user_progress
            WHERE user_id = ? AND lesson_id = ?
        """, (user_id, lesson_id))
        progress = cursor.fetchone()
        if progress and progress[0]:
            return "Вы уже завершили этот урок."

        # Отмечаем урок завершённым
        cursor.execute("""
            INSERT INTO user_progress (user_id, lesson_id, completed, completion_date)
            VALUES (?, ?, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, lesson_id) DO UPDATE SET completed = TRUE, completion_date = CURRENT_TIMESTAMP
        """, (user_id, lesson_id))
        conn.commit()
        return "Урок завершён."

def get_user_products(user_id: int):
    """Получает список продуктов, приобретённых пользователем."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        query = """
        SELECT products.id, products.name
        FROM purchases
        INNER JOIN products ON purchases.product_id = products.id
        WHERE purchases.user_id = ? AND products.is_hidden = 0
        """
        cursor.execute(query, (user_id,))
        products = cursor.fetchall()
        return [{"id": product[0], "name": product[1]} for product in products]
    finally:
        conn.close()



def get_course_progress(user_id, course_id):
    """
    Получает прогресс пользователя по курсу.

    :param user_id: ID пользователя.
    :param course_id: ID курса.
    :return: Словарь с данными о прогрессе (завершённые уроки, общее количество уроков).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Считаем общее количество уроков в курсе
    cursor.execute("""
        SELECT COUNT(*) 
        FROM lessons 
        WHERE course_id = ?
    """, (course_id,))
    total_lessons = cursor.fetchone()[0]

    # Считаем количество завершённых уроков для пользователя в этом курсе
    cursor.execute("""
        SELECT COUNT(*) 
        FROM user_progress 
        INNER JOIN lessons ON user_progress.lesson_id = lessons.id
        WHERE user_progress.user_id = ? AND lessons.course_id = ? AND user_progress.completed = 1
    """, (user_id, course_id))
    completed_lessons = cursor.fetchone()[0]

    conn.close()

    return {
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons
    }
def get_user_courses(user_id: int):
    """Получает список курсов, приобретённых пользователем."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        query = """
        SELECT courses.id, courses.name
        FROM purchases
        INNER JOIN courses ON purchases.course_id = courses.id
        WHERE purchases.user_id = ?
        """
        cursor.execute(query, (user_id,))
        courses = cursor.fetchall()
        return [{"id": course[0], "name": course[1]} for course in courses]
    finally:
        conn.close()



def save_course_progress(user_id, course_id, lesson_id, completed):
    """
    Сохраняет или обновляет прогресс пользователя по курсу.

    :param user_id: ID пользователя.
    :param course_id: ID курса.
    :param lesson_id: ID урока.
    :param completed: Флаг завершения урока (True/False).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем, существует ли запись прогресса для этого урока и пользователя
    cursor.execute("""
        SELECT id FROM user_progress 
        WHERE user_id = ? AND lesson_id = ?
    """, (user_id, lesson_id))
    result = cursor.fetchone()

    if result:
        # Если запись существует, обновляем её
        cursor.execute("""
            UPDATE user_progress
            SET completed = ?, completion_date = ?
            WHERE user_id = ? AND lesson_id = ?
        """, (completed, datetime.now(), user_id, lesson_id))
    else:
        # Если записи нет, создаём новую
        cursor.execute("""
            INSERT INTO user_progress (user_id, lesson_id, completed, completion_date)
            VALUES (?, ?, ?, ?)
        """, (user_id, lesson_id, completed, datetime.now()))

    conn.commit()
    conn.close()


def update_user_balance(user_id: int, new_balance: int):
    """Обновляет баланс пользователя."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)  # Разрешаем использование соединений в разных потоках
    cursor = conn.cursor()
    try:
        # Отладочное сообщение: проверим, что новое значение баланса правильное
        print(f"Обновление баланса пользователя {user_id} на {new_balance} VED")

        cursor.execute(
            """
            UPDATE users
            SET balance = ?
            WHERE user_id = ?
            """,
            (new_balance, user_id)
        )

        conn.commit()  # Применяем изменения
        print("Изменения в базе данных успешно применены.")
    except Exception as e:
        print(f"Ошибка при обновлении баланса: {e}")
    finally:
        conn.close()  # Закрываем соединение


def add_product_to_user(user_id: int, product_id: int):
    """Добавляет продукт в список покупок пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO purchases (user_id, product_id, purchase_date)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, product_id)
        )
        conn.commit()  # Применяем изменения
    finally:
        conn.close()  # Закрываем соединение
def get_user_purchase_for_product(user_id, product_id):
    """Функция для получения данных о покупке продукта пользователем."""
    # Создаём подключение к базе данных
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # SQL-запрос для получения последней покупки указанного продукта
    cursor.execute("""
        SELECT * FROM purchases
        WHERE user_id = ? AND product_id = ?
        ORDER BY purchase_date DESC
        LIMIT 1
    """, (user_id, product_id))

    # Извлекаем одну запись
    purchase = cursor.fetchone()

    # Закрываем соединение с базой данных
    conn.close()

    return purchase


def update_balance(user_id: int, amount: float):
    """
    Функция для обновления баланса пользователя в базе данных.

    :param user_id: ID пользователя
    :param amount: Сумма, на которую нужно обновить баланс
    """
    try:
        conn = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
        cursor = conn.cursor()

        # Проверяем, существует ли пользователь в базе
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            # Если пользователь существует, обновляем его баланс
            new_balance = result[0] + amount  # Прибавляем сумму к текущему балансу
            cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        else:
            # Если пользователя нет, добавляем нового
            cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, amount))

        conn.commit()  # Подтверждаем изменения
        cursor.close()
        conn.close()

    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
        return False

    return True


async def get_exchange_rate(selected_method):
    rates = {
        "BTC": 0.000058849008,  # Курс BTC к VED
        "USDT": 1.12,  # Курс USDT к VED (например, 1 USDT = 1 VED)
    }
    return rates.get(selected_method, 1.12)  # По умолчанию курс 1 для других методов

def add_aphorism(text: str, author: str):
    conn = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
    cursor = conn.cursor()
    cursor.execute("INSERT INTO aphorisms (text, author) VALUES (?, ?)", (text, author))
    conn.commit()
    conn.close()

def get_random_aphorism():
    conn = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
    cursor = conn.cursor()
    cursor.execute("SELECT text, author FROM aphorisms ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result

def add_image(file_id: str):
    conn = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
    cursor = conn.cursor()
    cursor.execute("INSERT INTO aphorism_images (file_id) VALUES (?)", (file_id,))
    conn.commit()
    conn.close()

def get_random_image():
    conn = sqlite3.connect(DB_PATH)  # Подключаемся к базе данных
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM aphorism_images ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_initial_rates():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS exchange_rates (
                currency TEXT PRIMARY KEY,
                rate TEXT
            );
        """)
        cursor.execute("INSERT OR IGNORE INTO exchange_rates (currency, rate) VALUES (?, ?)", ("USDT", "1.12"))
        cursor.execute("INSERT OR IGNORE INTO exchange_rates (currency, rate) VALUES (?, ?)", ("BTC", "0.000058849008"))
        conn.commit()
        conn.close()
        print("Начальные курсы валют установлены.")
    except Exception as e:
        print(f"Ошибка при установке начальных курсов валют: {e}")



def get_rate(currency):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT rate FROM exchange_rates WHERE currency = ?", (currency,))
        result = cursor.fetchone()
        if result is None:
            print(f"Курс валюты {currency} не найден в базе.")
        return result[0] if result else None
    except Exception as e:
        print(f"Ошибка при получении курса валюты {currency}: {e}")
        return None


def update_rate(currency, new_rate):
    try:
        # Преобразуем курс в строку, чтобы избежать его преобразования в экспоненциальную форму
        formatted_rate = "{:.12f}".format(new_rate)  # Преобразуем в строку с фиксированным числовым форматом

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO exchange_rates (currency, rate) VALUES (?, ?)", (currency, formatted_rate))
        conn.commit()
        conn.close()
        print(f"Курс {currency} успешно обновлён на {formatted_rate}")
    except Exception as e:
        print(f"Ошибка при обновлении курса валюты {currency}: {e}")
def execute_query(query, params=None):
    """Функция для выполнения запросов к базе данных."""
    conn = sqlite3.connect(DB_PATH)  # Замените на ваш путь к базе данных
    conn.row_factory = sqlite3.Row  # Устанавливаем row_factory для работы с результатами как с словарями
    cursor = conn.cursor()

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    result = cursor.fetchall()
    print("Query result:", result)  # Добавляем отладочный вывод для проверки результата
    conn.close()
    return result


def update_product_status(product_id, status):
    """Обновляет статус продукта в базе данных."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET status = ? WHERE id = ?", (status, product_id))
        conn.commit()


def get_pending_products():
    """Получаем продукты с полями 'id', 'name', 'description', 'category' и статусом 'pending'."""
    query = """
    SELECT id, name, description, price, is_subscription, subscription_period, partner_id, image, product_type, code, is_hidden, after_purchase, course_id, status, category
    FROM products WHERE status = 'pending'
    """

    # Получаем результаты запроса
    products = execute_query(query)

    # Преобразуем результат в список словарей для удобства
    return [{
        'id': row['id'],
        'name': row['name'],
        'description': row['description'],
        'price': row['price'],
        'is_subscription': row['is_subscription'],
        'subscription_period': row['subscription_period'],
        'partner_id': row['partner_id'],
        'image': row['image'],
        'product_type': row['product_type'],
        'code': row['code'],
        'is_hidden': row['is_hidden'],
        'after_purchase': row['after_purchase'],
        'course_id': row['course_id'],
        'status': row['status'],
        'category': row['category']  # Добавляем поле category
    } for row in products]


# Функция для получения всех тегов из базы данных
def get_all_tags():
    conn = sqlite3.connect(DB_PATH)  # Укажите правильное имя вашей БД
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT tag FROM product_tags")
        tags = cursor.fetchall()
        return [tag[0] for tag in tags]
    finally:
        cursor.close()
        conn.close()

def get_users_by_tag(tag): # для админов
    conn = sqlite3.connect(DB_PATH)  # Укажите правильное имя вашей БД
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM user_tag_subscriptions WHERE tag = ?", (tag,))
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

# Сохранение подписки пользователя на тег
def add_user_subscription(user_id, tag):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO user_tag_subscriptions (user_id, tag) VALUES (?, ?)",
                (user_id, tag),
            )
            conn.commit()
            return True  # Успешная подписка
        except sqlite3.IntegrityError:
            return False  # Уже подписан

def get_current_rewards():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT event_type, role, reward_amount FROM referral_rewards")
        rewards = cursor.fetchall()
    return rewards

# Функция для обновления бонуса в базе данных
def update_reward(event_type, role, reward_amount):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE referral_rewards SET reward_amount = ? WHERE event_type = ? AND role = ?",
            (reward_amount, event_type, role)
        )
        conn.commit()

def get_referral_bonus(event_type: str, role: str) -> int:
    """
    Получает бонус из БД на основе типа события и роли.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT reward_amount FROM referral_rewards
            WHERE event_type = ? AND role = ?
        """, (event_type, role))
        result = cursor.fetchone()
        return result[0] if result else 0  # Возвращаем бонус или 0, если запись не найдена

def get_all_products_two():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM products WHERE is_hidden = 0")  # Только видимые продукты
    products = cursor.fetchall()
    connection.close()

    return [{'id': product[0], 'name': product[1]} for product in products]

def get_users_by_product(product_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""SELECT u.user_id, u.username FROM users u
                      JOIN purchases p ON u.user_id = p.user_id
                      WHERE p.product_id = ?""", (product_id,))
    users = cursor.fetchall()
    print(f"Found users: {users}")  # Выводим список найденных пользователей
    connection.close()
    return [{'user_id': user[0], 'username': user[1]} for user in users]

def get_partner_products(partner_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, name FROM products 
        WHERE partner_id = ? AND is_hidden = 0
    """, (partner_id,))
    products = cursor.fetchall()
    connection.close()
    return [{'id': row[0], 'name': row[1]} for row in products]


logger = logging.getLogger(__name__)
def get_users_by_product_partner(partner_id, product_id):
    try:
        logger.debug(f"Подключение к базе данных с путём {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        logger.debug(f"Выполнение SQL запроса для partner_id={partner_id} и product_id={product_id}")
        cursor.execute("""
            SELECT DISTINCT p.user_id
            FROM purchases p
            JOIN products pr ON p.product_id = pr.id
            WHERE pr.partner_id = ? AND pr.id = ?
        """, (partner_id, product_id))

        result = cursor.fetchall()
        logger.debug(f"Результат запроса для partner_id={partner_id}, product_id={product_id}: {result}")

        users = [{'user_id': row[0]} for row in result]
        logger.debug(f"Пользователи для продукта {product_id} от партнёра {partner_id}: {users}")

        conn.close()
        return users
    except Exception as e:
        logger.error(f"Ошибка получения пользователей по продукту и партнёру: {e}")
        return []


def get_lessons_by_course_id(course_id):
    """Получение всех уроков для определенного курса по его ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Логируем запрос к базе данных
    logging.debug(f"Выполняем запрос для получения уроков для курса с ID {course_id}")

    cursor.execute("SELECT id, course_id, title, description, material_link FROM lessons WHERE course_id = ?",
                   (course_id,))
    lessons = cursor.fetchall()

    # Логируем результаты запроса
    logging.debug(f"Получены уроки для курса {course_id}: {lessons}")
    logging.debug(f"Количество найденных уроков: {len(lessons)}")

    conn.close()
    return lessons



def get_lesson_by_id_for_purchase(lesson_id):
    """Получение одного урока по его ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Возвращаем строки как словари
    cursor = conn.cursor()

    cursor.execute("SELECT id, course_id, title, description, material_link FROM lessons WHERE id = ?", (lesson_id,))
    lesson = cursor.fetchone()

    conn.close()
    return dict(lesson) if lesson else None


def get_questions_by_lesson_id(lesson_id):
    """Получение всех вопросов для определенного урока по его ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, lesson_id, text, options, correct_answer FROM questions WHERE lesson_id = ?",
                   (lesson_id,))
    questions = cursor.fetchall()

    # Преобразование списка кортежей в список словарей
    questions_list = [
        {
            "id": row[0],
            "lesson_id": row[1],
            "text": row[2],
            "options": row[3],
            "correct_answer": row[4]
        }
        for row in questions
    ]

    conn.close()
    return questions_list


def get_question_by_id(question_id):
    """Получение одного вопроса по его ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, lesson_id, text, options, correct_answer FROM questions WHERE id = ?", (question_id,))
    question = cursor.fetchone()

    conn.close()

    if question:
        # Возвращаем данные как словарь
        return {
            'id': question[0],
            'lesson_id': question[1],
            'text': question[2],
            'options': question[3],
            'correct_answer': question[4]
        }
    return None



def get_user_by_id(user_id):
    """Получение пользователя по его ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, first_name, balance, language FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    conn.close()
    return user



def get_product_by_id_for_purchases(product_id):
    try:
        # Логирование начала выполнения функции
        logging.debug(f"Запрос к базе данных для продукта с ID: {product_id}")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Извлекаем данные о продукте, включая partner_id
        cursor.execute("""
            SELECT id, name, description, price, image, category, code, after_purchase, is_subscription, subscription_period, course_id, partner_id
            FROM products 
            WHERE id = ?
        """, (product_id,))
        row = cursor.fetchone()

        if row:
            product = dict(row)
            product["is_subscription"] = bool(product["is_subscription"])

            # Если продукт не является подпиской, убираем поле subscription_period
            if not product["is_subscription"]:
                product.pop("subscription_period", None)

            # Логирование полученного продукта
            logging.debug(f"Полученные данные для продукта с ID {product_id}: {product}")

            # Проверка наличия course_id
            course_id = product.get("course_id")
            if course_id:
                logging.debug(f"Продукт с ID {product_id} связан с курсом с ID {course_id}")
                product["course_id"] = course_id
            else:
                logging.debug(f"Для продукта с ID {product_id} курс не найден.")

            # Проверка наличия partner_id
            partner_id = product.get("partner_id")
            logging.debug(f"partner_id для продукта с ID {product_id}: {partner_id}")
            product["partner_id"] = partner_id

            return product
        else:
            logging.warning(f"Продукт с ID {product_id} не найден в базе данных.")
            return None

    except sqlite3.DatabaseError as e:
        logging.error(f"Ошибка базы данных: {e}")
        return None
    finally:
        conn.close()



def get_product_and_partner_by_id(product_id):
    """Получение информации о продукте и партнёре по ID продукта."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Получаем продукт по ID
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()

    if product is None:
        conn.close()
        return None, None

    product_data = {
        'id': product[0],
        'name': product[1],
        'description': product[2],
        'price': product[3],
        'image': product[4],
        'type': product[5],
        'category': product[6],
        'code': product[7],
        'after_purchase': product[8],
        'is_subscription': product[9],
        'course_id': product[10],
        'partner_id': product[11]  # partner_id
    }

    # Логируем информацию о продукте
    print(f"Product data: {product_data}")

    # Получаем партнёра по partner_id
    partner_id = product_data['partner_id']
    cursor.execute("SELECT * FROM users WHERE id = ?", (partner_id,))
    partner = cursor.fetchone()

    if partner is None:
        conn.close()
        return product_data, None  # Партнёр не найден

    partner_data = {
        'id': partner[0],
        'username': partner[1],
        'full_name': partner[2],
        'email': partner[3]
    }

    conn.close()
    return product_data, partner_data


def get_product_by_id_for_purchases_two(product_id):
    # Функция для получения данных о продукте по ID
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()

    conn.close()
    if product:
        return {
            'id': product[0],
            'name': product[1],
            'description': product[2],
            'price': product[3],
            'image': product[4],
            'type': product[5],
            'category': product[6],
            'code': product[7],
            'after_purchase': product[8],
            'is_subscription': product[9],
            'course_id': product[10],
            'partner_id': product[11],  # partner_id из таблицы products
        }
    return None


def get_partner_by_id(partner_id):
    logging.debug(f"Ищем партнёра с ID {partner_id}")

    # Преобразуем partner_id в строку и убираем лишние пробелы
    partner_id = str(partner_id).strip()

    # Убедитесь, что соединение с базой данных открыто
    connection = sqlite3.connect(DB_PATH)  # Укажите путь к вашей базе данных
    cursor = connection.cursor()

    try:
        # Логируем запрос, который выполняется
        query = "SELECT * FROM partners WHERE partner_id = ?"
        logging.debug(f"Выполняем запрос: {query} с параметром {partner_id}")

        # Выполняем запрос для получения данных о партнёре по ID
        cursor.execute(query, (partner_id,))
        partner = cursor.fetchone()

        if partner:
            logging.debug(f"Партнёр найден: {partner}")
            return partner  # Возвращаем данные о партнёре
        else:
            logging.debug(f"Партнёр с ID {partner_id} не найден.")
            return None
    except sqlite3.Error as e:
        logging.error(f"Ошибка при запросе к базе данных: {e}")
        return None
    finally:
        # Закрываем соединение с базой данных
        cursor.close()
        connection.close()


def get_partner_by_product_id(product_id):
    # Функция для получения партнёра по product_id
    logging.debug(f"Ищем партнёра для продукта с ID {product_id}")

    # Получаем продукт по ID
    product = get_product_by_id_for_purchases(product_id)

    if product:
        partner_id = product.get('partner_id')
        if partner_id:
            # Логируем найденный partner_id
            logging.debug(f"Найден partner_id: {partner_id}")

            # Получаем партнёра по partner_id
            partner = get_partner_by_id(partner_id)

            if partner:
                logging.debug(f"Найден партнёр: {partner}")
                return partner
            else:
                logging.debug(f"Партнёр с ID {partner_id} не найден.")
                return None
        else:
            logging.debug(f"У продукта с ID {product_id} отсутствует partner_id.")
            return None
    else:
        logging.debug(f"Продукт с ID {product_id} не найден.")
        return None

def insert_partner_question(user_id, partner_id, product_id, question_id, question_text, user_message):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO partner_questions (user_id, partner_id, product_id, question_id, question_text, user_message, status)
        VALUES (?, ?, ?, ?, ?, ?, 'new')
    """, (user_id, partner_id, product_id, question_id, question_text, user_message))

    connection.commit()
    connection.close()

def get_unanswered_questions_by_partner(partner_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, product_id, question_id, question_text, user_message
        FROM partner_questions
        WHERE partner_id = ? AND status = 'new'
    """, (partner_id,))

    questions = [
        {"id": row[0], "product_id": row[1], "question_id": row[2], "question_text": row[3], "user_message": row[4]}
        for row in cursor.fetchall()
    ]

    connection.close()
    return questions


def mark_question_as_answered(question_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("UPDATE partner_questions SET status = 'answered' WHERE id = ?", (question_id,))
    connection.commit()
    connection.close()


def get_question_from_user_by_id(question_id: int) -> Optional[Dict]:
    """
    Получает вопрос из таблицы partner_questions по его ID.

    :param question_id: ID вопроса.
    :return: Словарь с данными вопроса или None, если вопрос не найден.
    """
    try:
        logging.debug(f"Попытка получить вопрос с ID {question_id} из базы данных.")

        # Подключение к базе данных
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            logging.debug(f"Соединение с базой данных установлено: {DB_PATH}")

            # Выполняем запрос к таблице partner_questions
            cursor.execute("""
                SELECT id, user_id, partner_id, product_id, question_id, question_text, user_message, status, created_at
                FROM partner_questions
                WHERE id = ?
            """, (question_id,))

            # Получаем результат
            row = cursor.fetchone()
            logging.debug(f"Результат запроса: {row}")

            if row:
                # Если вопрос найден, формируем словарь
                question = {
                    "id": row[0],
                    "user_id": row[1],
                    "partner_id": row[2],
                    "product_id": row[3],
                    "question_id": row[4],
                    "question_text": row[5],
                    "user_message": row[6],
                    "status": row[7],
                    "created_at": row[8],
                }
                logging.debug(f"Вопрос с ID {question_id} найден: {question}")
                return question
            else:
                logging.warning(f"Вопрос с ID {question_id} не найден в базе данных.")
                return None
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении вопроса с ID {question_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Неизвестная ошибка при получении вопроса с ID {question_id}: {e}")
        return None


def get_question_from_user_by_product_and_question_id(product_id: int, question_id: int) -> Optional[Dict]:
    """
    Получает вопрос из таблицы partner_questions по ID продукта и ID вопроса.

    :param product_id: ID продукта.
    :param question_id: ID вопроса.
    :return: Словарь с данными вопроса или None, если вопрос не найден.
    """
    try:
        logging.debug(f"Попытка получить вопрос с product_id {product_id} и question_id {question_id} из базы данных.")

        # Подключение к базе данных
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            logging.debug(f"Соединение с базой данных установлено: {DB_PATH}")

            # Выполняем запрос к таблице partner_questions по product_id и question_id
            cursor.execute("""
                SELECT id, user_id, partner_id, product_id, question_id, question_text, user_message, status, created_at
                FROM partner_questions
                WHERE product_id = ? AND question_id = ?
            """, (product_id, question_id))

            # Получаем результат
            row = cursor.fetchone()

            if row:
                # Если вопрос найден, формируем словарь
                question = {
                    "id": row[0],
                    "user_id": row[1],
                    "partner_id": row[2],
                    "product_id": row[3],
                    "question_id": row[4],
                    "question_text": row[5],
                    "user_message": row[6],
                    "status": row[7],
                    "created_at": row[8],
                }
                logging.debug(f"Вопрос с product_id {product_id} и question_id {question_id} найден: {question}")
                return question
            else:
                logging.warning(f"Вопрос с product_id {product_id} и question_id {question_id} не найден в базе данных.")
                return None
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении вопроса с product_id {product_id} и question_id {question_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Неизвестная ошибка при получении вопроса с product_id {product_id} и question_id {question_id}: {e}")
        return None


async def get_user_balance_perevod(username):
    logging.debug(f"Запрос баланса пользователя @{username}")
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute("SELECT balance FROM users WHERE username = ?", (username,))
        result = await cursor.fetchone()

    if result:
        balance = result[0]
        logging.debug(f"Баланс для @{username} получен: {balance} (Тип: {type(balance)})")
        # Преобразуем баланс в float, если это необходимо
        balance = float(balance) if isinstance(balance, (int, float)) else 0.0
        logging.debug(f"Баланс пользователя @{username} после преобразования: {balance}")
    else:
        logging.warning(f"Пользователь @{username} не найден в базе данных.")
        balance = 0.0

    return balance



async def update_user_balance_perevod(username, amount):
    logging.debug(f"Обновление баланса пользователя @{username}: изменение на {amount}")
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (amount, username))
        await conn.commit()
    logging.debug(f"Баланс пользователя @{username} успешно обновлён.")





def get_partners_with_status(status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Извлекаем все необходимые поля: id, name, credo, logo_url, show_in_list, status
    cursor.execute("SELECT id, name, credo, logo_url, show_in_list, status,partner_id FROM partners WHERE status = ?", (status,))
    partners = cursor.fetchall()
    conn.close()
    return partners
def get_partner_by_id_admin(partner_id):
    logging.debug(f"Ищем партнёра с ID {partner_id}")

    # Преобразуем partner_id в строку и убираем лишние пробелы
    partner_id = str(partner_id).strip()

    # Преобразуем partner_id в число, если это необходимо
    try:
        partner_id = int(partner_id)
    except ValueError:
        logging.error(f"Ошибка при преобразовании ID партнёра: {partner_id}")
        return None

    connection = sqlite3.connect(DB_PATH)  # Укажите путь к вашей базе данных
    cursor = connection.cursor()

    try:
        # Обновленный запрос, извлекающий все необходимые поля
        query = "SELECT id, name, credo, logo_url, show_in_list, status, partner_id FROM partners WHERE id = ?"
        logging.debug(f"Выполняем запрос: {query} с параметром {partner_id}")

        # Выполняем запрос для получения данных о партнёре по ID
        cursor.execute(query, (partner_id,))
        partner = cursor.fetchone()

        if partner:
            logging.debug(f"Партнёр найден: {partner}")
            return partner  # Возвращаем данные о партнёре
        else:
            logging.debug(f"Партнёр с ID {partner_id} не найден.")
            return None
    except sqlite3.Error as e:
        logging.error(f"Ошибка при запросе к базе данных: {e}")
        return None
    finally:
        cursor.close()
        connection.close()
def update_partner_status(partner_id, status):
    """Обновление статуса партнёрской заявки по partner_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Обновляем статус партнёра в таблице partners
        cursor.execute("UPDATE partners SET status = ? WHERE partner_id = ?", (status, partner_id))
        conn.commit()
        logging.info(f"Статус партнёра с partner_id={partner_id} обновлён на '{status}'.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении статуса партнёрской заявки с partner_id={partner_id}: {e}")
    finally:
        conn.close()




async def save_feedback_to_db(user_id: int, feedback_text: str):
    # Подключение к базе данных SQLite
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Запрос на вставку данных в таблицу
    cursor.execute(
        "INSERT INTO feedbacks (user_id, feedback_text) VALUES (?, ?)",
        (user_id, feedback_text)
    )

    # Сохранение изменений
    connection.commit()

    # Закрытие соединения
    connection.close()

def get_feedbacks():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("SELECT user_id, feedback_text, created_at FROM feedbacks ORDER BY created_at DESC")
    feedbacks = cursor.fetchall()  # получаем все строки

    connection.close()
    return feedbacks


def update_user_role_for_partner(user_id: int, new_role: str):
    try:
        # Создаем соединение с базой данных
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Выполняем запрос на обновление роли пользователя
        cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))

        # Применяем изменения
        conn.commit()

        print(f"Роль пользователя с ID {user_id} обновлена на {new_role}.")
    except sqlite3.Error as e:
        # Обработка ошибок, если они возникнут
        print(f"Ошибка при обновлении роли пользователя: {e}")
        conn.rollback()  # Откатываем изменения в случае ошибки
    finally:
        # Закрываем соединение
        conn.close()


def get_user_by_id_admin(user_id):
    """Получение пользователя по его user_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Добавьте поле 'role' в SELECT-запрос
        cursor.execute(
            "SELECT id, username, first_name, balance, user_id, language, role FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        # Преобразуем кортеж в словарь, если строка найдена
        if row:
            columns = [column[0] for column in cursor.description]  # Получаем имена столбцов
            user = dict(zip(columns, row))  # Создаём словарь из имен колонок и значений
            return user
        return None  # Возвращаем None, если пользователь не найден

    finally:
        conn.close()  # Закрываем соединение
def get_user_by_partner_id(partner_id):
    """Получение пользователя по partner_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ищем партнёра по ID
    cursor.execute("SELECT partner_id FROM partners WHERE id = ?", (partner_id,))
    partner = cursor.fetchone()

    if partner:
        # partner_id найден, используем его для поиска пользователя
        user_id = partner[0]
        cursor.execute("SELECT id, username, first_name, balance, language FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    else:
        user = None

    conn.close()
    return user

# Функция для получения всех типов продуктов
def get_all_product_types():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM product_types')
    product_types = cursor.fetchall()
    conn.close()
    return product_types

def get_popular_product_types():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pt.type, COUNT(p.id) AS product_count
        FROM products p
        JOIN product_types pt ON p.product_type = pt.type
        WHERE p.is_hidden = 0 AND p.status = 'approved'
        GROUP BY pt.type
        ORDER BY product_count DESC
        LIMIT 5
    """)
    result = cursor.fetchall()
    print(f"Результаты запроса: {result}")  # Вывод результатов запроса
    conn.close()
    return [{"type": row[0], "product_count": row[1]} for row in result]

def get_all_aphorisms() -> list:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, text, author FROM aphorisms")
        rows = cursor.fetchall()
        return [{"id": row[0], "text": row[1], "author": row[2]} for row in rows]

def aphorism_exists(aphorism_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:  # Замените "database.db" на путь к вашей базе данных
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM aphorisms WHERE id = ?", (aphorism_id,))
        return cursor.fetchone()[0] > 0

def delete_aphorism(aphorism_id: int):
    """
    Удаляет афоризм из базы данных по его ID.

    :param aphorism_id: ID афоризма, который нужно удалить
    """
    with sqlite3.connect(DB_PATH) as conn:  # Укажите путь к вашей базе данных
        cursor = conn.cursor()
        cursor.execute("DELETE FROM aphorisms WHERE id = ?", (aphorism_id,))
        if cursor.rowcount == 0:
            raise ValueError("Афоризм с указанным ID не найден.")
        conn.commit()

def update_aphorism_text(aphorism_id: int, new_text: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE aphorisms SET text = ? WHERE id = ?", (new_text, aphorism_id))
        if cursor.rowcount == 0:
            raise ValueError("Не удалось обновить текст афоризма. Проверьте ID.")
        conn.commit()

def update_aphorism_author(aphorism_id: int, new_author: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE aphorisms SET author = ? WHERE id = ?", (new_author, aphorism_id))
        if cursor.rowcount == 0:
            raise ValueError("Не удалось обновить автора афоризма. Проверьте ID.")
        conn.commit()


def get_admins():
    """
    Возвращает список ID администраторов из базы данных.
    """
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE role = 'admin'")
        return [row[0] for row in cursor.fetchall()]


def save_referral_system(levels, rewards):
    # Подключаемся к базе данных
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Вставляем данные в таблицу referral_system
        cursor.execute("""
            INSERT INTO referral_system (levels) 
            VALUES (?)
        """, (levels,))

        # Получаем ID недавно добавленной реферальной системы
        referral_system_id = cursor.lastrowid

        # Вставляем награды для каждого уровня в таблицу referral_rewards
        for level, reward in enumerate(rewards, start=1):
            # reward содержит два значения: за покупку и выигрыш в лотерее
            reward_types = ["purchase", "lottery"]
            for reward_type, amount in zip(reward_types, reward):
                cursor.execute("""
                    INSERT INTO referral_rewards (referral_system_id, level, reward_type, amount)
                    VALUES (?, ?, ?, ?)
                """, (referral_system_id, level, reward_type, amount))

        # Сохраняем изменения
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        # Закрываем соединение
        conn.close()


def get_all_users():
    # Подключение к базе данных
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Получаем всех пользователей
    cursor.execute("SELECT user_id, username FROM users")
    users = cursor.fetchall()

    # Закрываем соединение
    connection.close()

    # Преобразуем данные в список словарей
    return [{"user_id": user[0], "username": user[1]} for user in users]


def add_balance_to_user(user_id: int, amount: int) -> bool:
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        # Проверяем, существует ли пользователь
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if not result:
            return False

        # Обновляем баланс
        new_balance = result[0] + amount
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        connection.commit()
        return True
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
        return False
    finally:
        connection.close()

def get_lottery_settings():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ticket_price, current_round, lottery_active FROM lottery_settings WHERE id = 1")
        return cursor.fetchone()

def update_lottery_settings(ticket_price=None, current_round=None, lottery_active=None):
    with connect_db() as conn:
        cursor = conn.cursor()
        if ticket_price is not None:
            cursor.execute("UPDATE lottery_settings SET ticket_price = ? WHERE id = 1", (ticket_price,))
        if current_round is not None:
            cursor.execute("UPDATE lottery_settings SET current_round = ? WHERE id = 1", (current_round,))
        if lottery_active is not None:
            cursor.execute("UPDATE lottery_settings SET lottery_active = ? WHERE id = 1", (lottery_active,))
        conn.commit()

def add_ticket(user_id, ticket_number, round_number):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lottery_tickets (user_id, ticket_number, round)
            VALUES (?, ?, ?)
        """, (user_id, ticket_number, round_number))
        conn.commit()

def get_user_tickets(user_id, round_number):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_number, is_winner, prize
            FROM lottery_tickets
            WHERE user_id = ? AND round = ?
        """, (user_id, round_number))
        return cursor.fetchall()

def get_all_tickets(round_number):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, ticket_number
            FROM lottery_tickets
            WHERE round = ?
        """, (round_number,))
        return cursor.fetchall()

def mark_ticket_as_winner(ticket_id, prize):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE lottery_tickets
            SET is_winner = 1, prize = ?
            WHERE id = ?
        """, (prize, ticket_id))
        conn.commit()


async def get_user_language(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()

    if row:
        return row[0]  # Возвращаем язык
    return None  # Если язык не найден, возвращаем None


import pandas as pd
#test with excel
def load_texts(filepath):
    try:
        # Загружаем данные из Excel
        df = pd.read_excel(filepath)

        # Проверяем наличие необходимых столбцов
        if not all(col in df.columns for col in ['key', 'ru_text', 'en_text']):
            raise ValueError("Отсутствуют необходимые столбцы 'key', 'ru_text', 'en_text' в файле.")

        # Переводим данные в формат словаря
        texts = df.set_index('key')[['ru_text', 'en_text']].T.to_dict('dict')

        # Структурируем результат в нужный вид
        result = {k: {'ru': v['ru_text'], 'en': v['en_text']} for k, v in texts.items()}
        return result

    except Exception as e:
        print(f"Ошибка при загрузке текстов: {e}")
        return {}

def get_products_by_partner(partner_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, price, image, product_type, is_hidden, status, is_subscription, subscription_period, category FROM products WHERE partner_id = ?",
        (partner_id,))
    rows = cursor.fetchall()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "product_type": row[5],
            "is_hidden": bool(row[6]),
            "status": row[7],
            "is_subscription": bool(row[8]),  # Добавили флаг подписки
            "subscription_period": row[9],  # Добавили период подписки
            "category": row[10]  # Добавили категорию
            })
    return products

def get_current_referral_system():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, levels FROM referral_system ORDER BY id DESC LIMIT 1")
    system_result = cursor.fetchone()

    if system_result:
        referral_system_id, levels = system_result

        cursor.execute("""
            SELECT level, reward_type, amount 
            FROM referral_rewards 
            WHERE referral_system_id = ? 
            ORDER BY level, reward_type
        """, (referral_system_id,))
        rewards_result = cursor.fetchall()

        rewards = {}
        for level, reward_type, amount in rewards_result:
            if level not in rewards:
                rewards[level] = [0, 0]  # Предполагаем, что есть только два типа наград: покупка и лотерея
            if reward_type == 'purchase':
                rewards[level][0] = amount
            elif reward_type == 'lottery':
                rewards[level][1] = amount

        conn.close()
        return {'levels': levels, 'rewards': rewards}
    else:
        conn.close()
        return {'levels': 0, 'rewards': {}}


def update_referral_rewards(level: int, rewards: list[int]) -> None:
    conn = connect_db()
    cursor = conn.cursor()

    # Проверяем, что в таблице есть нужный referral_system_id для данного уровня
    cursor.execute("""
        SELECT id FROM referral_system WHERE levels >= ?
    """, (level,))

    referral_system_id = cursor.fetchone()

    if not referral_system_id:
        # Если подходящий referral_system_id не найден, выбрасываем ошибку
        raise ValueError(f"Нет подходящей реферальной системы для уровня {level}")

    referral_system_id = referral_system_id[0]  # Получаем идентификатор реферальной системы

    # Обновляем награды в зависимости от типа награды
    for reward_type, reward in zip(['purchase', 'lottery'], rewards):
        cursor.execute("""
            UPDATE referral_rewards 
            SET amount = ? 
            WHERE referral_system_id = ? AND level = ? AND reward_type = ?
        """, (reward, referral_system_id, level, reward_type))

    # Фиксируем изменения и закрываем соединение
    conn.commit()
    conn.close()


# Функция для создания реферальной системы
def create_referral_system(levels, rewards):
    try:
        connection = connect_db()  # Подключение к базе данных
        cursor = connection.cursor()

        # Вставка данных в таблицу referral_system
        cursor.execute('''
            INSERT INTO referral_system (levels)
            VALUES (?)
        ''', (levels,))
        referral_system_id = cursor.lastrowid  # Получаем ID только что добавленной реферальной системы

        # Вставка наград для каждого уровня
        for level, reward in enumerate(rewards, start=1):
            # Предположим, что reward - это список с двумя элементами: [за покупку, за выигрыш в лотерее]
            reward_purchase = reward[0]
            reward_lottery = reward[1]

            cursor.execute(''' 
                INSERT INTO referral_rewards (referral_system_id, level, reward_type, amount)
                VALUES (?, ?, ?, ?)
            ''', (referral_system_id, level, "purchase", reward_purchase))

            cursor.execute(''' 
                INSERT INTO referral_rewards (referral_system_id, level, reward_type, amount)
                VALUES (?, ?, ?, ?)
            ''', (referral_system_id, level, "lottery", reward_lottery))

        # Подтверждаем изменения в базе данных
        connection.commit()

        # Закрываем соединение с базой данных
        connection.close()

        # Логируем успешное создание
        print(f"Реферальная система создана с {levels} уровнями и наградами.")

    except Exception as e:
        # В случае ошибки выводим сообщение
        print(f"Ошибка при создании реферальной системы: {e}")

def get_referral_system_id() -> int:
    conn = connect_db()
    cursor = conn.cursor()

    # Получаем ID самой последней активной реферальной системы
    cursor.execute("""
        SELECT id FROM referral_system
        ORDER BY id DESC LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def get_referral_reward(referral_system_id: int, level: int) -> int:
    conn = connect_db()
    cursor = conn.cursor()

    # Получаем награду для заданного уровня и типа (покупка)
    cursor.execute("""
        SELECT amount FROM referral_rewards
        WHERE referral_system_id = ? AND level = ? AND reward_type = 'purchase'
    """, (referral_system_id, level))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else 0  # Возвращаем 0, если награды нет

def add_referral_reward(referrer_id: int, reward_amount: int) -> None:
    conn = connect_db()
    cursor = conn.cursor()

    # Обновляем баланс пригласившего пользователя
    cursor.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
    """, (reward_amount, referrer_id))

    # Фиксируем изменения и закрываем соединение
    conn.commit()
    conn.close()

def update_user_language(user_id: int, language: str):
    conn = connect_db()
    cursor = conn.cursor()

    # Обновление языка пользователя
    cursor.execute("""
        UPDATE users
        SET language = ?
        WHERE user_id = ?
    """, (language, user_id))

    # Сохранение изменений
    conn.commit()

    # Закрытие соединения
    conn.close()


# Функция для создания таблиц при запуске бота
if __name__ == "__main__":
    initialize_db()
