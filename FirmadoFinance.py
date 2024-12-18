import telebot
from telebot import types
import mysql.connector
from datetime import datetime


# Конфигурация для подключения к MySQL
DB_CONFIG = {
    'user': 'user',
    'password': 'password',
    'host': 'user.mysql.pythonanywhere-services.com',
    'database': 'user$database.db'
}


# Подключение к боту
API_TOKEN = 'TOKEN'
bot = telebot.TeleBot(API_TOKEN)


# Подключение к базе данных
def create_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# Создание таблиц при запуске
def create_tables():
    conn = create_db_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INT PRIMARY KEY,
            username VARCHAR(255),
            group_id INT DEFAULT NULL
        )
    ''')

    # Таблица групп для совместного учёта
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `groups` (
            group_id INT AUTO_INCREMENT PRIMARY KEY,
            group_name VARCHAR(255)
        )
    ''')

    # Таблица участников групп
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_users (
            user_id INT,
            group_id INT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (group_id) REFERENCES `groups` (group_id)
        )
    ''')

    # Таблица транзакций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            group_id INT DEFAULT NULL,
            amount FLOAT,
            transaction_type VARCHAR(255),
            category VARCHAR(255),
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (group_id) REFERENCES `groups` (group_id)
        )
    ''')

    # Таблица категорий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            category_type VARCHAR(255),  -- 'income' или 'expense'
            category_name VARCHAR(255),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()

create_tables()


# Регистрация пользователя
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    conn = create_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT IGNORE INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))
    conn.commit()
    cursor.close()
    conn.close()
    bot.reply_to(message, "Привет! Я помогу тебе вести учёт финансов. Используй /help для списка команд.")


# Команда помощи
@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message, """
Команды:
- /add_income — Добавить доход
- /add_expense — Добавить расход
- /balance — Посмотреть баланс
- /history — Посмотреть историю транзакций
- /categories — Управление категориями доходов/расходов
- /request_group — Запрос на совместный учёт
- /group_balance — Посмотреть баланс группы
""")


# Добавление дохода
@bot.message_handler(commands=['add_income'])
def add_income(message):
    msg = bot.reply_to(message, "Введите сумму дохода:")
    bot.register_next_step_handler(msg, process_income)


def process_income(message):
    try:
        amount = float(message.text)
        user_id = message.from_user.id

        # Получение категорий дохода
        conn = create_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category_name FROM categories WHERE user_id = %s AND category_type = 'income'", (user_id,))
        categories = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        if not categories:
            bot.reply_to(message, "У вас нет категорий дохода. Добавьте их с помощью команды /add_category.")
            return

        # Показ категорий кнопками
        markup = types.InlineKeyboardMarkup()
        for category in categories:
            markup.add(types.InlineKeyboardButton(category, callback_data=f"income_{category}_{amount}"))

        bot.reply_to(message, "Выберите категорию дохода:", reply_markup=markup)
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите правильную сумму.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("income_"))
def save_income(call):
    _, category, amount = call.data.split("_")
    user_id = call.from_user.id
    conn = create_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (user_id, amount, transaction_type, category) VALUES (%s, %s, 'income', %s)",
                   (user_id, amount, category))
    conn.commit()
    cursor.close()
    conn.close()
    bot.answer_callback_query(call.id, f"Доход в категории '{category}' на сумму {amount} добавлен.")


# Добавление расхода
@bot.message_handler(commands=['add_expense'])
def add_expense(message):
    msg = bot.reply_to(message, "Введите сумму расхода:")
    bot.register_next_step_handler(msg, process_expense)


def process_expense(message):
    try:
        amount = float(message.text)
        user_id = message.from_user.id

        # Получение категорий расхода
        conn = create_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category_name FROM categories WHERE user_id = %s AND category_type = 'expense'", (user_id,))
        categories = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        if not categories:
            bot.reply_to(message, "У вас нет категорий расхода. Добавьте их с помощью команды /add_category.")
            return

        # Показ категорий кнопками
        markup = types.InlineKeyboardMarkup()
        for category in categories:
            markup.add(types.InlineKeyboardButton(category, callback_data=f"expense_{category}_{amount}"))

        bot.reply_to(message, "Выберите категорию расхода:", reply_markup=markup)
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите правильную сумму.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("expense_"))
def save_expense(call):
    _, category, amount = call.data.split("_")
    user_id = call.from_user.id
    conn = create_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (user_id, amount, transaction_type, category) VALUES (%s, %s, 'expense', %s)",
                   (user_id, amount, category))
    conn.commit()
    cursor.close()
    conn.close()
    bot.answer_callback_query(call.id, f"Расход в категории '{category}' на сумму {amount} добавлен.")


@bot.message_handler(commands=['balance'])
def balance(message):
    user_id = message.from_user.id
    conn = create_db_connection()
    cursor = conn.cursor()

    # Доходы
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = %s AND transaction_type = 'income'", (user_id,))
    income = cursor.fetchone()[0] or 0

    # Расходы
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = %s AND transaction_type = 'expense'", (user_id,))
    expense = cursor.fetchone()[0] or 0

    cursor.close()
    conn.close()

    bot.reply_to(message, f"Ваш баланс:\nДоходы: {income} грн\nРасходы: {expense} грн")


# История транзакций
@bot.message_handler(commands=['history'])
def history(message):
    user_id = message.from_user.id
    conn = create_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT amount, transaction_type, category, date FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT 10", (user_id,))
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()

    if not transactions:
        bot.reply_to(message, "У вас пока нет транзакций.")
    else:
        history_text = "\n".join([f"{row[3]}: {row[1]} - {row[2]} - {row[0]} грн" for row in transactions])
        bot.reply_to(message, f"Последние транзакции:\n{history_text}")


# Управление категориями
@bot.message_handler(commands=['categories'])
def categories(message):
    user_id = message.from_user.id

    # Подключение к базе данных
    conn = create_db_connection()
    cursor = conn.cursor()

    # Получение категорий пользователя
    cursor.execute("SELECT category_type, category_name FROM categories WHERE user_id = %s", (user_id,))
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    # Формируем ответ
    if not categories:
        bot.reply_to(message, "У вас ещё нет категорий. Добавьте их с помощью команды /add_category или /bulk_add_categories.")
    else:
        category_list = "\n".join([f"- {cat[1]} ({cat[0]})" for cat in categories])
        #bot.reply_to(message, f"Ваши категории:\n{category_list}")
        bot.reply_to(message, f"Ваши категории:\n{category_list}\n\nДобавить категорию: /add_category\nУдалить категорию: /delete_category")


@bot.message_handler(commands=['bulk_add_categories'])
def bulk_add_categories(message):
    msg = bot.reply_to(
        message,
        "Введите тип категорий ('income' для доходов, 'expense' для расходов), затем перечислите категории через запятую.\n"
        "Пример: income Зарплата, Дивиденды, Продажа товара"
    )
    bot.register_next_step_handler(msg, process_bulk_add_categories)

def process_bulk_add_categories(message):
    try:
        # Разделяем тип и список категорий
        parts = message.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(message, "Пожалуйста, укажите тип и категории через пробел.")
            return

        category_type = parts[0].strip().lower()
        if category_type not in ['income', 'expense']:
            bot.reply_to(message, "Тип категории должен быть 'income' или 'expense'. Попробуйте снова.")
            return

        # Разделяем категории
        categories = [cat.strip() for cat in parts[1].split(",")]

        # Добавляем категории в базу данных
        user_id = message.from_user.id
        conn = create_db_connection()
        cursor = conn.cursor()

        for category in categories:
            cursor.execute(
                "INSERT INTO categories (user_id, category_type, category_name) VALUES (%s, %s, %s)",
                (user_id, category_type, category)
            )

        conn.commit()
        cursor.close()
        conn.close()

        bot.reply_to(
            message,
            f"Категории успешно добавлены:\n{', '.join(categories)}"
        )
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {e}")


@bot.message_handler(commands=['request_group'])
def request_group(message):
    msg = bot.reply_to(message, "Введите ID пользователя для совместного учёта:")
    bot.register_next_step_handler(msg, process_group_request)

def process_group_request(message):
    try:
        partner_id = int(message.text)
        user_id = message.from_user.id

        # Создаём группу
        group_name = f"Группа {user_id}-{partner_id}"
        conn = create_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO `groups` (group_name) VALUES (%s)", (group_name,))
        group_id = cursor.lastrowid

        # Отправляем запрос партнёру
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Принять", callback_data=f"accept_{user_id}_{partner_id}_{group_id}"),
            types.InlineKeyboardButton("Отклонить", callback_data=f"reject_{user_id}_{partner_id}")
        )
        bot.send_message(partner_id, f"Пользователь {user_id} приглашает вас в совместный учёт финансов.", reply_markup=markup)

        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"Запрос отправлен пользователю {partner_id}.")
    except ValueError:
        bot.reply_to(message, "ID пользователя должно быть числом.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("accept") or call.data.startswith("reject"))
def handle_group_response(call):
    conn = create_db_connection()
    cursor = conn.cursor()

    if call.data.startswith("accept"):
        _, user_id, partner_id, group_id = call.data.split("_")
        cursor.execute("INSERT INTO group_users (user_id, group_id) VALUES (%s, %s)", (user_id, group_id))
        cursor.execute("INSERT INTO group_users (user_id, group_id) VALUES (%s, %s)", (partner_id, group_id))
        conn.commit()
        bot.answer_callback_query(call.id, "Вы приняли запрос на совместный учёт.")
    elif call.data.startswith("reject"):
        _, user_id, partner_id = call.data.split("_")
        bot.answer_callback_query(call.id, "Вы отклонили запрос.")

    cursor.close()
    conn.close()


@bot.message_handler(commands=['add_category'])
def add_category(message):
    msg = bot.reply_to(
        message,
        "Введите тип категории ('income' для дохода, 'expense' для расхода), а затем её название (например, income Зарплата):"
    )
    bot.register_next_step_handler(msg, process_add_category)

def process_add_category(message):
    try:
        # Разделяем тип категории и её название
        category_type, category_name = message.text.split(" ", 1)
        if category_type not in ['income', 'expense']:
            bot.reply_to(message, "Тип категории должен быть 'income' или 'expense'. Попробуйте снова.")
            return

        # Получаем ID пользователя
        user_id = message.from_user.id

        # Добавляем категорию в базу данных
        conn = create_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (user_id, category_type, category_name) VALUES (%s, %s, %s)",
            (user_id, category_type, category_name)
        )
        conn.commit()
        cursor.close()
        conn.close()

        bot.reply_to(message, f"Категория '{category_name}' добавлена в тип '{category_type}'.")
    except ValueError:
        bot.reply_to(message, "Пожалуйста, укажите тип и название категории через пробел.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")


@bot.message_handler(commands=['delete_category'])
def delete_category(message):
    msg = bot.reply_to(message, "Введите название категории, которую хотите удалить:")
    bot.register_next_step_handler(msg, process_delete_category)


def process_delete_category(message):
    category_name = message.text
    user_id = message.from_user.id

    conn = create_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE user_id = %s AND category_name = %s", (user_id, category_name))
    conn.commit()
    deleted_rows = cursor.rowcount
    cursor.close()
    conn.close()

    if deleted_rows > 0:
        bot.reply_to(message, f"Категория '{category_name}' удалена.")
    else:
        bot.reply_to(message, f"Категория '{category_name}' не найдена.")

bot.polling()
