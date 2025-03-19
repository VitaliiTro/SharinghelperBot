import data
import asyncio
import logging
import sqlite3
import datetime
import os

from aiogram.enums.parse_mode import ParseMode
from PIL import Image
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from aiogram import F
from aiogram.types import ContentType
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from babel.dates import format_date





API_TOKEN = data.token
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

owner = data.owner
worker = data.worker

logging.basicConfig(filename='Sharinghelper.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Form(StatesGroup):
    user = State()
    ID = State()


@dp.message(Command("id"))
async def start_message(message: types.Message):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /id")

    await message.answer("Ваш ID: " + str(message.from_user.id))


@dp.message(Command("start"))
async def start_message(message: types.Message):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /start")

    await bot.send_message(message.chat.id, 'Вітаю. Це бот-помічник "ПРОКАТайся🛴"!\n'
                                            'Для роботи з ботом користуйтесь командами з Меню')




def get_scooters_by_city(city: str):
    logging.info(f"Функція викликана для отримання самокатів у місті: {city}")

    conn = sqlite3.connect("base_scooters.db")
    cursor = conn.cursor()

    query = """
    SELECT NUMBER_SCOOTER
    FROM SCOOTERS  
    WHERE LOWER(TRIM(city)) = LOWER(TRIM(?))
    """

    cursor.execute(query, (city,))
    scooters = cursor.fetchall()

    conn.close()

    scooters_list = [scooter[0] for scooter in scooters]
    logging.info(f"Знайдено {len(scooters_list)} самокатів у місті {city}")

    return scooters_list


def get_cities():
    conn = sqlite3.connect("base_scooters.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT CITY FROM users WHERE from_work IS NULL AND period_work IS NULL")
    cities = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cities







class Users(StatesGroup):
    user_name = State()
    surname = State()
    name = State()
    patronymic = State()
    birthday = State()
    age = State()
    phone_number = State()
    city = State()
    position = State()
    to_work = State()
    from_work = State()
    period_work = State()
    photo_passport = State()
    comment = State()
    responsible_employer = State()


class REPAIRS(StatesGroup):
    DATE_REPAIR = State()
    WORKER_PERSON = State()
    CITY = State()
    NAME_SCOOTER = State()
    TYPE_REPAIR = State()
    REPAIR = State()
    COMMENT = State()
    PHOTO_REPAIR = State()
    RESPONSIBLE_PERSON = State()



class PURCHASES(StatesGroup):
    DATE_BOUGHT = State()
    BUYER_PERSON = State()
    CITY = State()
    PURCHASE = State()
    QUANTITY = State()
    COST_PURCHASE = State()
    REASON_PURCHASE = State()
    COMMENT = State()
    PHOTO_PURCHASE = State()
    RESPONSIBLE_PERSON = State()

class DELETE_USER(StatesGroup):
        USER_NAME = State()
        CITY = State()
        FOR_WORK = State()


# 🔹 Визначаємо стан
class PurchaseState(StatesGroup):
    purchase_person = State()  


# 🔹 Статична клавіатура міст
keyboard_city = ReplyKeyboardBuilder()
keyboard_city.row(types.KeyboardButton(text="Канів"),
                types.KeyboardButton(text="Лубни"))
keyboard_city.row(types.KeyboardButton(text="Прилуки"))


keyboard_type_repair = ReplyKeyboardBuilder()
keyboard_type_repair.row(types.KeyboardButton(text="Заміна деталі"),
                         types.KeyboardButton(text="Ремонт"))

keyboard_position = ReplyKeyboardBuilder()
keyboard_position.row(types.KeyboardButton(text="Технік, Диспетчер"),
                types.KeyboardButton(text="Технік"))
keyboard_position.row(types.KeyboardButton(text="Диспетчер"),
                types.KeyboardButton(text="Менеджер"))





@dp.message(Command("user_delete"))
async def delete_user(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /user_delete")

    if message.from_user.id in owner:
            await state.set_state(DELETE_USER.CITY)
            await message.reply("*для відміни натисніть на команду /cancel_user_delete\n\n"
                                "Оберіть місто", reply_markup=keyboard_city.as_markup(resize_keyboard=True))
    else:
        await bot.send_message(message.chat.id, "Ви не маєте доступу до даної функції!\U0001F4A2\n")
        await bot.send_message(message.chat.id, 'Якщо хочете отримати доступ до закритої команди: \n'
                                                'відправте @vvitalino команду та скопійований номер'
                                                + str(message.from_user.id))


@dp.message(Command("cancel_user_delete"))
async def delete_user(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /cancel_user_delete")

    current_state = await state.get_state()
    if current_state is None:
        return

    # Очищення стану
    await state.clear()
    await message.reply('Стан було скинуто!',reply_markup=types.ReplyKeyboardRemove())



# Обробник вибору міста
@dp.message(DELETE_USER.CITY)
async def city_selected(message: types.Message, state: FSMContext):
    await state.update_data(CITY=message.text)
    data = await state.get_data()
    city = data.get("CITY")

    if not city:
        await message.reply("Помилка: місто не вибрано.")
        return

    # Підключення до бази даних
    conn = sqlite3.connect("base_scooters.db")
    cursor = conn.cursor()

    # Виконання SQL-запиту з перевіркою NULL та порожнього рядка
    cursor.execute(
        """SELECT user_name 
           FROM users 
           WHERE CITY = ? 
           AND (from_work IS NULL OR from_work = '') 
           AND (period_work IS NULL OR period_work = '')""",
        (city,)
    )

    # Отримання списку імен
    users = [row[0] for row in cursor.fetchall()]

    # Закриття підключення до БД
    conn.close()

    if not users:
        await message.reply("Немає кого звільняти для обраного міста", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        await message.reply("Стан скинуто")
        return
    def get_users_keyboard(users, row_width=2):
        builder = ReplyKeyboardBuilder()
        for user in users:
            builder.button(text=str(user))
        return builder.adjust(row_width).as_markup(resize_keyboard=True)

    keyboard = get_users_keyboard(users, row_width=2)

    await state.set_state(DELETE_USER.USER_NAME)
    await message.reply("Оберіть працівника:", reply_markup=keyboard)



@dp.message(DELETE_USER.USER_NAME)
async def user_selected(message: types.Message, state: FSMContext):
    await state.update_data(USER_NAME=message.text)
    await message.reply("Введіть дату звільнення (РРРР-ММ-ДД)", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(DELETE_USER.FOR_WORK)


@dp.message(DELETE_USER.FOR_WORK)
async def get_leave_date(message: types.Message, state: FSMContext):
    try:
        # Отримуємо дату звільнення від користувача
        from_work = datetime.datetime.strptime(message.text, "%Y-%m-%d").date()

        # Отримуємо дані з FSM
        data = await state.get_data()
        user_name = data.get("USER_NAME")

        if not user_name:
            await message.reply("Помилка: працівник не вибраний")
            return

        # Підключення до бази
        conn = sqlite3.connect("base_scooters.db")
        cursor = conn.cursor()

        # Отримуємо дату прийому на роботу (`to_work`)
        cursor.execute(
            """SELECT to_work 
               FROM users 
               WHERE user_name = ? 
               AND (from_work IS NULL OR TRIM(from_work) = '') 
               AND responsible_employer_status LIKE '%погоджено%'""",
            (user_name,)
        )

        to_work = cursor.fetchone()

        # Якщо користувач не знайдений або дата `to_work` відсутня
        if not to_work or not to_work[0]:
            await message.reply("Помилка: не вдалося знайти дату прийому на роботу.")
            conn.close()
            return

        # Розрахунок періоду роботи
        to_work_date = datetime.datetime.strptime(to_work[0], "%Y-%m-%d").date()
        delta = from_work - to_work_date
        years, remainder = divmod(delta.days, 365)
        months, days = divmod(remainder, 30)
        period_work = f"{years} years, {months} months, {days} days"

        # Оновлення даних у БД

        update_query = f'''
                UPDATE users 
                SET from_work = ?, period_work = ? 
                WHERE user_name = ?;
            '''

        cursor.execute(update_query, (from_work, period_work, user_name))

        conn.commit()
        conn.close()
        # Повідомлення про успішне оновлення
        await message.reply("Дані успішно оновлені у БД!")

        # Завершуємо стан
        await state.clear()

    except ValueError:
        await message.reply("Невірний формат дати, спробуйте ще раз (РРРР-ММ-ДД).")




'''///////////////////////////////////////////////////////////////////////////////////////////////////////////'''


@dp.message(Command("user"))
async def add_user(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /user")

    if message.from_user.id in owner:
        await state.set_state(Users.surname)
        await message.reply("Формування службової по створенню користувача розпочато!\n"
                            "Права на помилку НЕМАЄ - будьте уважні!\n\n"
                            "*для відміни натисніть на команду /cancel_user\n\n"
                            "Введіть прізвище працівника")
    else:
        await bot.send_message(message.chat.id, "Ви не маєте доступу до даної функції!\U0001F4A2\n")
        await bot.send_message(message.chat.id, 'Якщо хочете отримати доступ до закритої команди: \n'
                                                'відправте @vvitalino команду та скопійований номер'
                                                + str(message.from_user.id))





@dp.message(Command("cancel_user"))
async def add_user(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /cancel_user")

    current_state = await state.get_state()
    if current_state is None:
        return

    # Очищення стану
    await state.clear()
    await message.reply('Стан було скинуто!')



@dp.message(Users.surname)
async def process_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await state.set_state(Users.name)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть ім'я працівника")


@dp.message(Users.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Users.patronymic)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть по-батькові працівника")


@dp.message(Users.patronymic)
async def process_patronymic(message: types.Message, state: FSMContext):
    await state.update_data(patronymic=message.text)
    await state.set_state(Users.birthday)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть дату дня народження працівника\n"
                        "у форматі YYYY-MM-DD (наприклад, 2002-05-11)")


@dp.message(Users.birthday)
async def process_age(message: types.Message, state: FSMContext):
    birthday = message.text.strip()

    def is_valid_date(date_text):
        try:
            datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
            return True
        except ValueError:
            return False

    if not is_valid_date(birthday):
        await message.answer("Введіть коректну дату у форматі YYYY-MM-DD (наприклад, 2002-05-11)")
        return

    await state.update_data(birthday=message.text)
    await state.set_state(Users.phone_number)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть номер телефону працівника\n"
                        "(лише цифри, від 10 до 12 символів, можливо з '+')")


@dp.message(Users.phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    phone_number = message.text.strip()

    def is_valid_phone(phone_number):
        return (phone_number.startswith('+') and phone_number[1:].isdigit() and 10 <= len(phone_number[1:]) <= 12) or \
               (phone_number.isdigit() and 10 <= len(phone_number) <= 12)

    if not is_valid_phone(phone_number):
        await message.answer("Введіть коректний номер телефону (лише цифри, від 10 до 12 символів, можливо з '+')")
        return

    await state.update_data(phone_number=message.text)
    await state.set_state(Users.city)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть місто працівника", reply_markup=keyboard_city.as_markup(resize_keyboard=True))


@dp.message(Users.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(Users.position)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть посаду роботи", reply_markup=keyboard_position.as_markup(resize_keyboard=True))
    

@dp.message(Users.position)
async def process_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text)
    await state.set_state(Users.to_work)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть дату прийняття на роботу", reply_markup=types.ReplyKeyboardRemove())


@dp.message(Users.to_work)
async def process_to_work(message: types.Message, state: FSMContext):
    to_work = message.text.strip()

    def is_valid_date(date_text):
        try:
            datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
            return True
        except ValueError:
            return False

    if not is_valid_date(to_work):
        await message.answer("Введіть коректну дату у форматі YYYY-MM-DD (наприклад, 2023-08-16)")
        return

    await state.update_data(to_work=message.text)
    await state.set_state(Users.comment)
    await message.reply("*для відміни натисніть на команду /cancel_user\n\n"
                        "Введіть коментар про працівника")
    

@dp.message(Users.comment)
async def process_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await state.set_state(Users.photo_passport)
    await message.reply("ОБОВ'ЯЗКОВО НАДІШЛІТЬ ОДНЕ ФОТО ПАСПОРТУ!\n"
                        "ОДНЕ ЯКІСНЕ ФОТО!")



# Обробник фото
@dp.message(Users.photo_passport, F.content_type == ContentType.PHOTO)
async def process_photo_passport(message: types.Message, state: FSMContext):
    temp = await state.get_data()
    photos = temp.get("photos", [])

    # Додаємо нове фото до списку
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)

    # Перевіряємо, чи отримано достатньо фото
    if len(photos) < 2:  
        await message.reply("НАДІШЛІТЬ ФОТО ПАСПОРТУ З ІНШОЇ СТОРОНИ")
        return

    # Завантажуємо фото в тимчасові файли
    file_paths = []
    for i, file_id in enumerate(photos):
        file_path = f"data/temp_user_photo_passport/temp_{file_id}_{i}.jpg"
        file_paths.append(file_path)
        await bot.download(file_id, destination=file_path)
    
    # Об'єднуємо зображення
    images = [Image.open(fp) for fp in file_paths]
    widths, heights = zip(*(img.size for img in images))
    combined_image = Image.new("RGB", (max(widths), sum(heights)))
    
    y_offset = 0
    for img in images:
        combined_image.paste(img, (0, y_offset))
        y_offset += img.size[1]
    
    # Зберігаємо комбіноване фото
    combined_path = f"data/user_photo_passport/{photos[0]}.jpg"
    combined_image.save(combined_path)
    name_combined_photo = f"{photos[0]}"

    # Видаляємо тимчасові файли
    for fp in file_paths:
        os.remove(fp)

    # Отримання інших даних
    date = datetime.datetime.now().strftime("%H:%M  %Y-%m-%d")
    birthday_date = datetime.datetime.strptime(temp['birthday'], "%Y-%m-%d").date()
    to_work_date = datetime.datetime.strptime(temp['to_work'], "%Y-%m-%d").date()
    age = to_work_date.year - birthday_date.year - ((to_work_date.month, to_work_date.day) < (birthday_date.month, birthday_date.day))
    user_name = temp['surname'] + " " + temp['name'] + " " + temp['patronymic']
    
    temp.update({
        'user_name': user_name,
        'age': age,
        'responsible_employer': "Троянов Віталій",
        'date': date,
        'responsible_employer_status': "не розглянуто \U0001F937",
        'photo_passport': name_combined_photo 
    })
    
    text = (f"СЛУЖБОВА: ПРИЙНЯТТЯ НА РОБОТУ\n"
            f"[{temp['date']}]\n"
            f"ПІБ: {temp['user_name']}\n"
            f"ДЕНЬ НАРОДЖЕННЯ: {temp['birthday']}\n"
            f"ВІК: {temp['age']}\n"
            f"НОМЕР ТЕЛЕФОНУ: {temp['phone_number']}\n"
            f"МІСТО: {temp['city']}\n"
            f"ПОСАДА: {temp['position']}\n"
            f"ПРИЙНЯТО НА РОБОТУ: {temp['to_work']}\n"
            f"КОМЕНТАР: {temp['comment']}\n\n"
            f"ВІДПОВІДАЛЬНА ОСОБА\n"
            f"{temp['responsible_employer']} - {temp['responsible_employer_status']}")
    
    photo_passport = FSInputFile(combined_path)
    IMPORTANT = await bot.send_photo(chat_id=data.scooter_chat, message_thread_id=data.scooter_users,
                                     photo=photo_passport, caption=text)
    
    temp['user_id'] = message.from_user.id
    temp['chat_id'] = IMPORTANT.chat.id
    temp['thread_id'] = IMPORTANT.message_thread_id  
    temp['message_id'] = IMPORTANT.message_id

    # Збереження в БД
    conn = sqlite3.connect('base_scooters.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users (date, user_id, user_name, surname, name, patronymic, birthday, age, phone_number, city, position, to_work, 
                                        comment, responsible_employer, responsible_employer_status, photo_passport, chat_id, thread_id, message_id) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''',
                   (temp['date'], temp['user_id'], temp['user_name'], temp['surname'], temp['name'], temp['patronymic'], temp['birthday'],
                    temp['age'], temp['phone_number'], temp['city'], temp['position'], temp['to_work'], temp['comment'],
                    temp['responsible_employer'], temp['responsible_employer_status'], temp['photo_passport'], temp['chat_id'],
                    temp['thread_id'], temp['message_id']))
    id_sluzhbova = cursor.lastrowid
    conn.commit()
    conn.close()
    
    
    await message.reply(f"Службову по прийнятті на роботу зафіксовано!\nCлужбова №{id_sluzhbova}",
                        parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())

    await state.clear()

'''////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////'''




def get_buyers_by_city(city: str):
    logging.info(f"Функція викликана для міста: {city}")

    conn = sqlite3.connect("base_scooters.db")
    cursor = conn.cursor()

    query = """
    SELECT surname, name 
    FROM users 
    WHERE 
        (from_work IS NULL OR TRIM(from_work) = '') 
        AND (to_work IS NOT NULL AND TRIM(to_work) != '') 
        AND responsible_employer_status LIKE '%погоджено%' 
        AND LOWER(TRIM(CITY)) = LOWER(TRIM(?))
    """  

    cursor.execute(query, (city,))
    buyers = cursor.fetchall()

    conn.close()

    logging.info(f"Кількість покупців: {len(buyers)}")  # ✅ Перевірка

    for buyer in buyers:
        logging.info(f"Покупець: {buyer[0]} {buyer[1]}")  # ✅ Логування покупців

    return [f"{buyer[0]} {buyer[1]}" for buyer in buyers] if buyers else []


 



@dp.message(Command("purchase"))
async def add_purchase(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /purchase")


    if message.from_user.id in worker or owner:
        await state.set_state(PURCHASES.CITY)
        await message.reply("Формування службової покупки розпочато!\n"
                            "Права на помилку НЕМАЄ - будьте уважні!\n\n"
                            "*для відміни натисніть на команду /cancel_purchase\n\n"
                            "Оберіть місто", reply_markup=keyboard_city.as_markup(resize_keyboard=True))
    else:
        await bot.send_message(message.chat.id, "Ви не маєте доступу до даної функції!\U0001F4A2\n")
        await bot.send_message(message.chat.id, 'Якщо хочете отримати доступ до закритої команди: \n'
                                                'відправте @vvitalino команду та скопійований номер'
                                                + str(message.from_user.id))



@dp.message(Command("cancel_purchase"))
async def add_user(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /cancel_purchase")

    current_state = await state.get_state()
    if current_state is None:
        return

    # Очищення стану
    await state.clear()
    await message.reply('Стан було скинуто!', reply_markup=types.ReplyKeyboardRemove())


'''
@dp.message(PURCHASES.DATE_BOUGHT)
async def process_date_bought(message: types.Message, state: FSMContext):
    date_bought = message.text.strip()

    def is_valid_date(date_text):
        try:
            datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
            return True
        except ValueError:
            return False

    if not is_valid_date(date_bought):
        await message.answer("Введіть коректну дату у форматі YYYY-MM-DD (наприклад, 2024-07-15)")
        return

    await state.update_data(DATE_BOUGHT=message.text)
    await state.set_state(PURCHASES.CITY)
    await message.reply("*для відміни натисніть на команду /cancel_purchase\n\n"
                        "Введіть місто", reply_markup=keyboard_city.as_markup(resize_keyboard=True))'''


@dp.message(lambda message: message.text in ["Канів", "Лубни", "Прилуки"], PURCHASES.CITY)
async def process_city_buyers_selection(message: types.Message, state: FSMContext):
    await state.update_data(CITY=message.text)

    if message.from_user.id in owner:

        await state.set_state(PURCHASES.BUYER_PERSON)
        await state.update_data(BUYER_PERSON="Троянов Віталій")

        await state.set_state(PURCHASES.PURCHASE)
        await message.reply(
            "<code>Нова пошта</code>\n"
            "<code>Інструмент</code>\n"
            "<code>Побутові витрати</code>\n"
            "<code>Деталі</code>\n"
            "<code>Сто, шиномонтаж</code>\n"  
            "<code>Ремонт</code>\n"  
            "<code></code>\n\n\n"

            "\U0001F6ABРІДКО ВИКОРИСТОВУЮТЬСЯ\U0001F6AB\n"
            "<code>Оренда</code>\n"
            "<code>Електроенергія</code>\n"
            "<code>ЗП</code>\n"
            "<code>Сім-карти(Інтернет)</code>\n"
            "<code>Роялті</code>\n"
            "<code>Ремонт(Хмельницький)</code>\n"
            "<code>Податки</code>\n"
            "<code>Товари для самокатів</code>\n"
            "<code>Паливо</code>\n"
            "<code>Відрядження</code>\n"
            "<code>Реклама</code>\n"
            "<code>Переобладнання самоката(Хмельницький)</code>\n"


            "\n\nВведіть ПОКУПКУ (список можливих покупок наведено вище). Щоб скопіювати назву"
            " покупки достатньо по ній натиснути: ",
            reply_markup=types.ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)

    else:
        city = message.text
        buyers = get_buyers_by_city(city)

        buyers_str = ', '.join(buyers) if buyers else '-----'

        await state.set_state(PURCHASES.BUYER_PERSON)


        await state.update_data(BUYER_PERSON=buyers_str)



        await state.set_state(PURCHASES.PURCHASE)
        await message.reply(
            "<code>Нова пошта</code>\n"
            "<code>Інструмент</code>\n"
            "<code>Побутові витрати</code>\n"
            "<code>Деталі</code>\n"
            "<code>Сто, шиномонтаж</code>\n"  
            "<code>Ремонт</code>\n"          


            "\n\nВведіть ПОКУПКУ (список можливих покупок наведено вище). Щоб скопіювати назву"
            " покупки достатньо по ній натиснути: ",
            reply_markup=types.ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)




@dp.message(PURCHASES.PURCHASE)
async def process_purchase(message: types.Message, state: FSMContext):
    await state.update_data(PURCHASE=message.text)
    await state.set_state(PURCHASES.COST_PURCHASE)
    await message.reply("*для відміни натисніть на команду /cancel_purchase\n\n"
                        "Введіть вартість покупки")


@dp.message(PURCHASES.COST_PURCHASE)
async def process_cost_purchase(message: types.Message, state: FSMContext):
    await state.update_data(COST_PURCHASE=message.text)
    await state.set_state(PURCHASES.COMMENT)
    await message.reply("*для відміни натисніть на команду /cancel_purchase\n\n"
                        "Введіть коментар")


@dp.message(PURCHASES.COMMENT)
async def process_comment(message: types.Message, state: FSMContext):
    await state.update_data(COMMENT=message.text)
    await state.set_state(PURCHASES.PHOTO_PURCHASE)
    await message.reply("ОБОВ'ЯЗКОВО НАДІШЛІТЬ ОДНЕ ФОТО ПОКУПКИ!\n"
                        "ОДНЕ ЯКІСНЕ ФОТО!")



@dp.message(PURCHASES.PHOTO_PURCHASE, F.content_type == ContentType.PHOTO)
async def process_photo_purchase(message: types.Message, state: FSMContext):

    file_name = f"data/photo_purchase/{message.photo[-1].file_id}.jpg"
    await bot.download(message.photo[-1], destination=file_name)

    status = "не розглянуто \U0001F937"
    temp = await state.get_data()
    now = datetime.datetime.now().strftime("%H:%M  %Y-%m-%d")
    now2 = datetime.datetime.now()
    month_ua = format_date(now2, "LLLL", locale="uk")


    temp['RESPONSIBLE_PERSON'] = "Троянов Віталій"
    temp['RESPONSIBLE_PERSON_STATUS'] = status
    temp['DATE'] = now
    temp['MONTH'] = month_ua
    temp['PHOTO_PURCHASE'] = message.photo[-1].file_id
    
    text = (f"СЛУЖБОВА 🛒ПОКУПКА🛒:  {temp['DATE']}\n"
            f"ПОКУПЕЦЬ: {temp['BUYER_PERSON']}\n"
            f"МІСТО: {temp['CITY']}\n"
            f"ПОКУПКА: {temp['PURCHASE']}\n"
            f"ВАРТІСТЬ: {temp['COST_PURCHASE']}\n"
            f"КОМЕНТАР: {temp['COMMENT']}\n\n"            
            f"ВІДПОВІДАЛЬНА ОСОБА\n"
            f"{temp['RESPONSIBLE_PERSON']} - {temp['RESPONSIBLE_PERSON_STATUS']}")
    
    photo_purchase = FSInputFile(file_name)
    IMPORTANT = await bot.send_photo(chat_id=data.scooter_chat, message_thread_id=data.scooter_purchases,
                                     photo=photo_purchase, caption=text)
    
    temp['USER_ID'] = message.from_user.id
    temp['CHAT_ID'] = IMPORTANT.chat.id
    temp['THREAD_ID'] = IMPORTANT.message_thread_id
    temp['MESSAGE_ID'] = IMPORTANT.message_id

    # Збереження в БД
    conn = sqlite3.connect('base_scooters.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO PURCHASES (DATE, USER_ID, MONTH, BUYER_PERSON, CITY, PURCHASE, 
                            COST_PURCHASE, COMMENT, PHOTO_PURCHASE, RESPONSIBLE_PERSON, 
                            RESPONSIBLE_PERSON_STATUS, CHAT_ID, THREAD_ID, MESSAGE_ID) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''',
                   (temp['DATE'], temp['USER_ID'], temp['MONTH'], temp['BUYER_PERSON'], temp['CITY'],
                    temp['PURCHASE'], temp['COST_PURCHASE'], temp['COMMENT'],
                    temp['PHOTO_PURCHASE'], temp['RESPONSIBLE_PERSON'], temp['RESPONSIBLE_PERSON_STATUS'],
                    temp['CHAT_ID'], temp['THREAD_ID'], temp['MESSAGE_ID']))
    purchase_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    
    await message.reply(f"Службову по покупці зафіксовано!\nCлужбова №{purchase_id}", parse_mode="HTML",
                            reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

'''////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////'''

def get_worker_person_by_city(city: str):
    logging.info(f"Функція викликана для міста: {city}")

    conn = sqlite3.connect("base_scooters.db")
    cursor = conn.cursor()

    query = """
    SELECT surname, name 
    FROM users 
    WHERE 
        (from_work IS NULL OR TRIM(from_work) = '') 
        AND (to_work IS NOT NULL AND TRIM(to_work) != '') 
        AND responsible_employer_status LIKE '%погоджено%' 
        AND LOWER(TRIM(CITY)) = LOWER(TRIM(?))
    """

    cursor.execute(query, (city,))
    buyers = cursor.fetchall()

    conn.close()

    logging.info(f"Кількість покупців: {len(buyers)}")  # ✅ Перевірка

    for buyer in buyers:
        logging.info(f"Покупець: {buyer[0]} {buyer[1]}")  # ✅ Логування покупців

    return [f"{buyer[0]} {buyer[1]}" for buyer in buyers] if buyers else []


@dp.message(Command("repair"))
async def add_repair(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /repair")

    if message.from_user.id in worker or owner:
        await state.set_state(REPAIRS.CITY)
        await message.reply("Формування службової по ремонту розпочато!\n"
                            "Права на помилку НЕМАЄ - будьте уважні!\n\n"
                            "*для відміни натисніть на команду /cancel_repair\n\n"
                            "Оберіть місто", reply_markup=keyboard_city.as_markup(resize_keyboard=True))

    else:
        await bot.send_message(message.chat.id, "Ви не маєте доступу до даної функції!\U0001F4A2\n")
        await bot.send_message(message.chat.id, 'Якщо хочете отримати доступ до закритої команди: \n'
                                                'відправте @vvitalino команду та скопійований номер'
                                                + str(message.from_user.id))



@dp.message(Command("cancel_repair"))
async def add_repair(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} - {message.from_user.username} натиснув команду /cancel_repair")

    current_state = await state.get_state()
    if current_state is None:
        return

    # Очищення стану
    await state.clear()
    await message.reply('Стан було скинуто!', reply_markup=types.ReplyKeyboardRemove())

'''
@dp.message(REPAIRS.DATE_REPAIR)
async def process_date_repair(message: types.Message, state: FSMContext):
    date_repair = message.text.strip()

    def is_valid_date(date_text):
        try:
            datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
            return True
        except ValueError:
            return False

    if not is_valid_date(date_repair):
        await message.answer("Введіть коректну дату у форматі YYYY-MM-DD (наприклад, 2024-10-31)")
        return

    await state.update_data(DATE_REPAIR=message.text)
    await state.set_state(REPAIRS.CITY)
    await message.reply("*для відміни натисніть на команду /cancel_repair\n\n"
                        "Оберіть місто", reply_markup=keyboard_city.as_markup(resize_keyboard=True))
'''

@dp.message(lambda message: message.text in ["Канів", "Лубни", "Прилуки"], REPAIRS.CITY)
async def process_city_repairs_selection(message: types.Message, state: FSMContext):
    logging.info(f"Користувач вибрав місто: {message.text}")
    await state.update_data(CITY=message.text)

    data = await state.get_data()
    logging.info(f"Стан після збереження міста: {data}")

    city = message.text
    buyers = get_worker_person_by_city(city)

    buyers_str = ', '.join(buyers) if buyers else '-----'

    await state.set_state(REPAIRS.WORKER_PERSON)
    await state.update_data(WORKER_PERSON=buyers_str)

    await state.set_state(REPAIRS.NAME_SCOOTER)

    data = await state.get_data()
    city = data.get("CITY")

    if not city:
        await message.reply("Помилка: місто не вибрано. Будь ласка, спочатку виберіть місто",
                            reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return

    logging.info(f"Функція викликана для отримання самокатів у місті: {city}")

    city = message.text
    scooters = get_scooters_by_city(city)  # Функція, яка повертає список самокатів

    if not scooters:
        await message.reply("Самокати у цьому місті не знайдені", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return

    logging.info(f"Знайдено {len(scooters)} самокатів у місті {city}")


    def get_scooter_keyboard(scooters, row_width=2):
        builder = ReplyKeyboardBuilder()
        for scooter in scooters:
            builder.button(text=str(scooter))
        return builder.adjust(row_width).as_markup(resize_keyboard=True)

    keyboard = get_scooter_keyboard(scooters, row_width=6)


    await state.set_state(REPAIRS.NAME_SCOOTER)
    await message.reply("*для відміни натисніть на команду /cancel_repair\n\n"
                        "Оберіть номер самокату", reply_markup=keyboard)


@dp.message(REPAIRS.NAME_SCOOTER)
async def process_name_scooter(message: types.Message, state: FSMContext):
    await state.update_data(NAME_SCOOTER=message.text)
    await state.set_state(REPAIRS.TYPE_REPAIR)
    await message.reply("*для відміни натисніть на команду /cancel_repair\n\n"
                        "Оберіть вид ремонту", reply_markup=keyboard_type_repair.as_markup(resize_keyboard=True))





@dp.message(lambda message: message.text in ["Заміна деталі"], REPAIRS.TYPE_REPAIR)
async def process_type_repair(message: types.Message, state: FSMContext):
    await state.update_data(TYPE_REPAIR=message.text)
    await state.set_state(REPAIRS.REPAIR)
    await message.reply(
                        "<code>Шини неоригінальні + антипрокольна рідина</code>\n"
                        "<code>Шини литі</code>\n"
                        "<code>Ручка газу</code>\n"
                        "<code>Ручка тормозу</code>\n"
                        "<code>Втулка+болти+гайки механізму складання</code>\n"
                        "<code>Язичок складання</code>\n"
                        "<code>Втулка до язичка складання</code>\n"
                        "<code>Гальмівні колодки</code>\n"
                        "<code>Передня вилка</code>\n"
                        "<code>Фара (прожектор) передня</code>\n"
                        "<code>Дзвінок</code>\n"
                        "<code>Кабель з'єднання BLE (голови)</code>\n"
                        "<code>Тормозний тросік</code>\n"
                        "<code>Лапка (підніжка)</code>\n"
                        "<code>Гріпси звичайні на руль (пара)</code>\n"
                        "<code>Гріпси шерінгові на руль (пара)</code>\n"
                        "<code>Пластикове кільце фіксатор вузла складування</code>\n"
                        "<code>Переднє крило</code>\n"
                        "<code>Заднє крило з малим стопом в зборі</code>\n"
                        "<code>Резинові заглушки (3 шт)</code>\n"
                        "<code>Захисна панель спідометра (bLE)</code>\n\n\n"
                
                
                        "\U00002699ПІДШИПНИКИ, ПРОСТАВКИ\U00002699\n"
                        "<code>Передні підшипники</code>\n"
                        "<code>Шайби в мотор-колесо</code>\n"
                        "<code>Шайби(збільш. діаметру) в мотор-колесо</code>\n"
                        "<code>Задні підшипники</code>\n\n\n"
                        
                        
                        "\U0001F6ABРІДКО ВИКОРИСТОВУЮТЬСЯ\U0001F6AB\n"
                        "<code>Гальмівний диск</code>\n"
                        "<code>Руль в зборі (той, на якому гріпси та спідометр)</code>\n"
                        "<code>Рульова труба+вузол складування</code>\n"
                        "<code>Контролер (мат плата)</code>\n"
                        "<code>Плата голови BLE (спідометр)</code>\n"
                        "<code>Плата БМС в акумулятор)</code>\n"
                        "<code>Пластикові накладки на передню вилку</code>\n"
                        "<code>Пластикові накладки для задніх болтів</code>\n"
                        "<code>Кришка деки</code>\n"
                        "<code>Розпарні кольці для вилки (пара)</code>\n"
                        "<code>Гальмівний диск</code>\n"
                        "<code>Дека (корпус, там де акум і вся електроніка)</code>\n"
                        "<code>Гумовий килимок для деки</code>\n"
                        "<code>Переднє колесо+шина</code>\n"
                        "<code>Мотор-колесо+шина</code>\n"
                        "<code>Трекер</code>\n"


                        "\n\nВведіть деталь (список можливих деталей наведено вище). Щоб скопіювати назву"
                        " деталі достатньо по ній натиснути: ",
                        reply_markup=types.ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)


@dp.message(lambda message: message.text in ["Ремонт"], REPAIRS.TYPE_REPAIR)
async def process_type_repair(message: types.Message, state: FSMContext):
    await state.update_data(TYPE_REPAIR=message.text)
    await state.set_state(REPAIRS.REPAIR)
    await message.reply(
        "<code>Переклейка труби</code>\n"
        "<code>Промазка переднього колеса</code>\n"
        "<code>Промазка заднього колеса</code>\n\n\n"

        "\U0001F6ABРІДКО ВИКОРИСТОВУЮТЬСЯ\U0001F6AB\n"


        "\n\nВведіть ремонт (список можливих деталей наведено вище). Щоб скопіювати назву"
        " ремонту достатньо по ній натиснути: ",
        reply_markup=types.ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)






@dp.message(REPAIRS.REPAIR)
async def process_type_repair(message: types.Message, state: FSMContext):
    await state.update_data(REPAIR=message.text)
    temp = await state.get_data()
    date = datetime.datetime.now().strftime("%H:%M  %Y-%m-%d")
    date_repair = datetime.datetime.now().strftime("%Y-%m-%d")

    temp.update({
        'RESPONSIBLE_PERSON': "Троянов Віталій",
        'DATE': date,
        'RESPONSIBLE_PERSON_STATUS': "не розглянуто \U0001F937"
    })

    text = (f"СЛУЖБОВА 🔧РЕМОНТ🔧: {temp['DATE']}\n"
            f"МІСТО: {temp['CITY']}\n"
            f"ПРАЦІВНИК: {temp['WORKER_PERSON']}\n"
            f"НОМЕР САМОКАТУ: {temp['NAME_SCOOTER']}\n"
            f"ВИД РЕМОНТУ: {temp['TYPE_REPAIR']}\n"
            f"ДЕТАЛЬ\РЕМОНТ: {temp['REPAIR']}\n\n"
            f"ВІДПОВІДАЛЬНА ОСОБА\n"
            f"{temp['RESPONSIBLE_PERSON']} - {temp['RESPONSIBLE_PERSON_STATUS']}")



    IMPORTANT = await bot.send_message(chat_id=data.scooter_chat, message_thread_id=data.scooter_repairs,
                                        text=text)

    temp['DATE_REPAIR'] = date_repair
    temp['USER_ID'] = message.from_user.id
    temp['CHAT_ID'] = IMPORTANT.chat.id
    temp['THREAD_ID'] = IMPORTANT.message_thread_id
    temp['MESSAGE_ID'] = IMPORTANT.message_id

    # Збереження в БД
    conn = sqlite3.connect('base_scooters.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO REPAIRS (USER_ID, DATE, DATE_REPAIR, CITY, WORKER_PERSON, NAME_SCOOTER, 
                            TYPE_REPAIR, REPAIR, RESPONSIBLE_PERSON,
                            RESPONSIBLE_PERSON_STATUS, CHAT_ID, THREAD_ID, MESSAGE_ID) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''',
                   (temp['USER_ID'], temp['DATE'], temp['DATE_REPAIR'], temp['CITY'], temp['WORKER_PERSON'],
                    temp['NAME_SCOOTER'], temp['TYPE_REPAIR'], temp['REPAIR'],
                    temp['RESPONSIBLE_PERSON'], temp['RESPONSIBLE_PERSON_STATUS'],
                    temp['CHAT_ID'], temp['THREAD_ID'], temp['MESSAGE_ID']))
    repair_id = cursor.lastrowid
    conn.commit()
    conn.close()

    await message.reply(f"Службову по ремонту зафіксовано!\nCлужбова №{repair_id}", parse_mode="HTML",
                        reply_markup=types.ReplyKeyboardRemove())

    await state.clear()


'''//////////////////////////////////////////////////////////////////////////////////////////////////////////////////'''





@dp.message_reaction()
async def message_reaction_handler(message_reaction: types.MessageReactionUpdated):

    if message_reaction.user.id == data.Troianov_VV:
        await handle_users_reactions(message_reaction)

    if message_reaction.user.id == data.Troianov_VV:
        await handle_purchases_reactions(message_reaction)

    if message_reaction.user.id == data.Troianov_VV:
        await handle_repairs_reactions(message_reaction)
    else:
        return


async def handle_users_reactions(message_reaction):
    temp_new_emoji_data = str(message_reaction.new_reaction)

    # Троянов Віталій 578548261

    RESPONSIBLE_EMPLOYER = [578548261]


    if message_reaction.user.id in RESPONSIBLE_EMPLOYER:
        new_info = "responsible_employer_status"
    else:
        return

    if "👍" in temp_new_emoji_data:
        status_update = "погоджено \U0001F44D"
    elif "👎" in temp_new_emoji_data:
        status_update = "відхилено \U0001F44E"
    elif "💩" in temp_new_emoji_data:
        status_update = "допрацювати \U0001F4A9"
    elif "" in temp_new_emoji_data:
        status_update = "не розглянуто \U0001F937"
    else:
        return

    conn = sqlite3.connect('base_scooters.db')
    cursor = conn.cursor()

    message_id = message_reaction.message_id

    update_query = f'''
            UPDATE users
            SET {new_info} = ?
            WHERE message_id = ?;
        '''

    cursor.execute(update_query, (status_update, message_id))

    select_query = f'''
            SELECT * FROM users
            WHERE message_id = ?;
        '''

    cursor.execute(select_query, (message_id,))
    rows = cursor.fetchall()

    conn.commit()
    conn.close()

    if not rows:
        print("В БД відсутні записи для MESSAGE_ID:", message_id)
        return

    try:
        for row in rows:
            (
                id, date, user_id, user_name, surname, name, patronymic, birthday, age, phone_number, city, position, to_work,
                from_work, comment, responsible_employer, responsible_employer_status, period_work, photo_passport,
                chat_id, thread_id, message_id
            ) = row

        text = (
                f"ДАТА СЛУЖБОВОЇ: {date}\n"
                f"ПІБ: {user_name}\n"
                f"ДЕНЬ НАРОДЖЕННЯ: {birthday}\n"
                f"ВІК: {age}\n"
                f"НОМЕР ТЕЛЕФОНУ: {phone_number}\n"
                f"МІСТО: {city}\n"
                f"ПОСАДА: {position}\n"
                f"ПРИЙНЯТО НА РОБОТУ: {to_work}\n"
                f"КОМЕНТАР: {comment}\n\n"
                f"ВІДПОВІДАЛЬНА ОСОБА\n"
                f"{responsible_employer} - {responsible_employer_status}")    

        await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text)

    except Exception as e:
        print("SHIT:" + str(e))

    try:        
        if "👍" in temp_new_emoji_data and \
                responsible_employer_status == "погоджено \U0001F44D":
            ready_text = "\U00002705СЛУЖБОВУ ОПРАЦЬОВАНО\U00002705\n" + text
            photo_passport = FSInputFile(f"data/user_photo_passport/{photo_passport}.jpg")
            important = await bot.send_photo(chat_id=chat_id, message_thread_id=data.scooter_users_finish,
                                             photo=photo_passport, caption=ready_text)

            old_thread_id = important.message_thread_id
            old_message_id = important.message_id

            conn = sqlite3.connect('base_scooters.db')
            cursor = conn.cursor()
            update_query = f'''
                            UPDATE users
                            SET thread_id = ?, message_id = ?
                            WHERE message_id = ?;
                            '''

            cursor.execute(update_query, (old_thread_id, old_message_id, message_id))
            conn.commit()
            conn.close()

            new_chat_id = chat_id
            new_message_id = message_id

            link = "https://t.me/c/2448053501/" + str(old_thread_id) + "/" + str(old_message_id)

            correct_datatime = datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
            new_text = "\U00002705СЛУЖБОВУ ОПРАЦЬОВАНО\U00002705" \
                       "\nДАТА СЛУЖБОВОЇ: " + str(date) + \
                       "\nПІБ: " + " " + str(user_name) + \
                       "\nДЕНЬ НАРОДЖЕННЯ: " + str(birthday) + \
                       "\nВІК: " + str(age) + \
                       "\nНОМЕР ТЕЛЕФОНУ: " + str(phone_number) + \
                       "\nМІСТО: " + str(city) + \
                       "\nПОСАДА: " + str(position) + \
                       "\nПРИЙНЯТО НА РОБОТУ: " + str(to_work) + \
                       "\nКОМЕНТАР: " + str(comment) + \
                       "\n\nВІДПОВІДАЛЬНА ОСОБА\n" + \
                       "" + str(responsible_employer) + "-" + str(responsible_employer_status) + \
                       "\n\nДАТА ОПРАЦЮВАННЯ: " + str(correct_datatime) + "\n" + link

            await bot.edit_message_caption(chat_id=new_chat_id, message_id=new_message_id, caption=new_text)

        elif "👎" in temp_new_emoji_data and \
                responsible_employer_status == "відхилено \U0001F44E":
            del_text = "\U0001F6ABСЛУЖБОВУ ВІДХИЛЕНО\U0001F6AB\n" + text
            photo_passport = FSInputFile(f"data/user_photo_passport/{photo_passport}.jpg")
            important = await bot.send_photo(chat_id=chat_id, message_thread_id=data.scooter_users_finish,
                                             photo=photo_passport, caption=del_text)

            old_thread_id = important.message_thread_id
            old_message_id = important.message_id

            conn = sqlite3.connect('base_scooters.db')
            cursor = conn.cursor()
            update_query = f'''
                            UPDATE users
                            SET thread_id = ?, message_id = ?
                            WHERE message_id = ?;
                            '''
            cursor.execute(update_query, (old_thread_id, old_message_id, message_id))
            conn.commit()
            conn.close()

            new_chat_id = chat_id
            new_message_id = message_id

            link = "https://t.me/c/2448053501/" + str(old_thread_id) + "/" + str(old_message_id)

            correct_datatime = datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
            new_text = "\U0001F6ABСЛУЖБОВУ ВІДХИЛЕНО\U0001F6AB" \
                       "\nДАТА СЛУЖБОВОЇ: " + str(date) + \
                       "\nПІБ: " + " " + str(user_name) + \
                       "\nДЕНЬ НАРОДЖЕННЯ: " + str(birthday) + \
                       "\nВІК: " + str(age) + \
                       "\nНОМЕР ТЕЛЕФОНУ: " + str(phone_number) + \
                       "\nМІСТО: " + str(city) + \
                       "\nПОСАДА: " + str(position) + \
                       "\nПРИЙНЯТО НА РОБОТУ: " + str(to_work) + \
                       "\nКОМЕНТАР: " + str(comment) + \
                       "\n\nВІДПОВІДАЛЬНА ОСОБА\n" + \
                       "" + str(responsible_employer) + "-" + str(responsible_employer_status) + \
                       "\n\nДАТА ОПРАЦЮВАННЯ: " + str(correct_datatime) + "\n" + link

            await bot.edit_message_caption(chat_id=new_chat_id, message_id=new_message_id, caption=new_text)
    except Exception as e:
        print("ATENTION: " + str(e))



async def handle_purchases_reactions(message_reaction):
    temp_new_emoji_data = str(message_reaction.new_reaction)

    # Троянов Віталій 578548261
    
    RESPONSIBLE_PERSON = [578548261]


    if message_reaction.user.id in RESPONSIBLE_PERSON:
        new_info = "RESPONSIBLE_PERSON_STATUS"
    else:
        return

    if "👍" in temp_new_emoji_data:
        status_update = "погоджено \U0001F44D"
    elif "👎" in temp_new_emoji_data:
        status_update = "відхилено \U0001F44E"
    elif "💩" in temp_new_emoji_data:
        status_update = "допрацювати \U0001F4A9"
    elif "" in temp_new_emoji_data:
        status_update = "не розглянуто \U0001F937"
    else:
        return

    conn = sqlite3.connect('base_scooters.db')
    cursor = conn.cursor()

    message_id = message_reaction.message_id

    update_query = f'''
            UPDATE PURCHASES
            SET {new_info} = ?
            WHERE MESSAGE_ID = ?;
        '''

    cursor.execute(update_query, (status_update, message_id))

    select_query = f'''
            SELECT * FROM PURCHASES
            WHERE MESSAGE_ID = ?;
        '''

    cursor.execute(select_query, (message_id,))
    rows = cursor.fetchall()

    conn.commit()
    conn.close()

    if not rows:
        print("В БД відсутні записи для MESSAGE_ID:", message_id)
        return


    try:
        for row in rows:
            (
                ID, DATE, MONTH, USER_ID, DATE_BOUGHT, BUYER_PERSON, CITY, PURCHASE, QUANTITY, COST_PURCHASE,
                REASON_PURCHASE, COMMENT, PHOTO_PURCHASE, RESPONSIBLE_PERSON, RESPONSIBLE_PERSON_STATUS, CHAT_ID,
                THREAD_ID, MESSAGE_ID
            ) = row

        text = (
                f"ДАТА СЛУЖБОВОЇ: {DATE}\n"
                f"ПОКУПЕЦЬ: {BUYER_PERSON}\n"
                f"МІСТО: {CITY}\n"
                f"ПОКУПКА: {PURCHASE}\n"
                f"ВАРТІСТЬ: {COST_PURCHASE}\n"
                f"КОМЕНТАР: {COMMENT}\n\n"                
                f"ВІДПОВІДАЛЬНА ОСОБА\n"
                f"{RESPONSIBLE_PERSON} - {RESPONSIBLE_PERSON_STATUS}")


        await bot.edit_message_caption(chat_id=CHAT_ID, message_id=MESSAGE_ID, caption=text)
    except Exception as e:
        print("SHIT:" + str(e))

    try:        
        if "👍" in temp_new_emoji_data and \
                RESPONSIBLE_PERSON_STATUS == "погоджено \U0001F44D":
            ready_text = "\U00002705СЛУЖБОВУ ОПРАЦЬОВАНО\U00002705\n" + text
            photo_purchase = FSInputFile(f"data/photo_purchase/{PHOTO_PURCHASE}.jpg")
            important = await bot.send_photo(chat_id=CHAT_ID, message_thread_id=data.scooter_purchases_finish,
                                             photo=photo_purchase, caption=ready_text)

            old_thread_id = important.message_thread_id
            old_message_id = important.message_id

            conn = sqlite3.connect('base_scooters.db')
            cursor = conn.cursor()
            update_query = f'''
                            UPDATE PURCHASES
                            SET THREAD_ID = ?, MESSAGE_ID = ?
                            WHERE MESSAGE_ID = ?;
                            '''

            cursor.execute(update_query, (old_thread_id, old_message_id, message_id))
            conn.commit()
            conn.close()

            new_chat_id = CHAT_ID
            new_message_id = MESSAGE_ID

            link = "https://t.me/c/2448053501/" + str(old_thread_id) + "/" + str(old_message_id)

            correct_datatime = datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
            new_text = "\U00002705СЛУЖБОВУ ОПРАЦЬОВАНО\U00002705" \
                       "\nДАТА СЛУЖБОВОЇ: " + str(DATE) + \
                       "\nПОКУПЕЦЬ: " + str(BUYER_PERSON) + \
                       "\nМІСТО: " + str(CITY) + \
                       "\nПОКУПКА: " + str(PURCHASE) + \
                       "\nВАРТІСТЬ: " + str(COST_PURCHASE) + \
                       "\nКОМЕНТАР: " + str(COMMENT) + \
                       "\n\nВІДПОВІДАЛЬНА ОСОБА\n" + \
                       "" + str(RESPONSIBLE_PERSON) + "-" + str(RESPONSIBLE_PERSON_STATUS) + \
                       "\n\nДАТА ОПРАЦЮВАННЯ: " + str(correct_datatime) + "\n" + link

            await bot.edit_message_caption(chat_id=new_chat_id, message_id=new_message_id, caption=new_text)

        elif "👎" in temp_new_emoji_data and \
                RESPONSIBLE_PERSON_STATUS == "відхилено \U0001F44E":
            del_text = "\U0001F6ABСЛУЖБОВУ ВІДХИЛЕНО\U0001F6AB\n" + text
            photo_purchase = FSInputFile(f"data/photo_purchase/{PHOTO_PURCHASE}.jpg")
            important = await bot.send_photo(chat_id=CHAT_ID, message_thread_id=data.scooter_purchases_finish,
                                             photo=photo_purchase, caption=del_text)

            old_thread_id = important.message_thread_id
            old_message_id = important.message_id

            conn = sqlite3.connect('base_scooters.db')
            cursor = conn.cursor()
            update_query = f'''
                            UPDATE PURCHASES
                            SET THREAD_ID = ?, MESSAGE_ID = ?
                            WHERE MESSAGE_ID = ?;
                            '''
            cursor.execute(update_query, (old_thread_id, old_message_id, message_id))
            conn.commit()
            conn.close()

            new_chat_id = CHAT_ID
            new_message_id = MESSAGE_ID

            link = "https://t.me/c/2448053501/" + str(old_thread_id) + "/" + str(old_message_id)

            correct_datatime = datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
            new_text = "\U0001F6ABСЛУЖБОВУ ВІДХИЛЕНО\U0001F6AB" \
                       "\nДАТА СЛУЖБОВОЇ: " + str(DATE) + \
                       "\nПОКУПЕЦЬ: " + str(BUYER_PERSON) + \
                       "\nМІСТО: " + str(CITY) + \
                       "\nПОКУПКА: " + str(PURCHASE) + \
                       "\nВАРТІСТЬ: " + str(COST_PURCHASE) + \
                       "\nКОМЕНТАР: " + str(COMMENT) + \
                       "\n\nВІДПОВІДАЛЬНА ОСОБА\n" + \
                       "" + str(RESPONSIBLE_PERSON) + "-" + str(RESPONSIBLE_PERSON_STATUS) + \
                       "\n\nДАТА ОПРАЦЮВАННЯ: " + str(correct_datatime) + "\n" + link

            await bot.edit_message_caption(chat_id=new_chat_id, message_id=new_message_id, caption=new_text)
    except Exception as e:
        print("ATENTION: " + str(e))


'''///////////////////////////////////////////////////////////////////////////////////////////'''


async def handle_repairs_reactions(message_reaction):
    temp_new_emoji_data = str(message_reaction.new_reaction)

    # Троянов Віталій 578548261

    RESPONSIBLE_PERSON = [578548261]


    if message_reaction.user.id in RESPONSIBLE_PERSON:
        new_info = "RESPONSIBLE_PERSON_STATUS"
    else:
        return

    if "👍" in temp_new_emoji_data:
        status_update = "погоджено \U0001F44D"
    elif "👎" in temp_new_emoji_data:
        status_update = "відхилено \U0001F44E"
    elif "💩" in temp_new_emoji_data:
        status_update = "допрацювати \U0001F4A9"
    elif "" in temp_new_emoji_data:
        status_update = "не розглянуто \U0001F937"
    else:
        return

    conn = sqlite3.connect('base_scooters.db')
    cursor = conn.cursor()

    message_id = message_reaction.message_id

    update_query = f'''
            UPDATE REPAIRS
            SET {new_info} = ?
            WHERE MESSAGE_ID = ?;
        '''

    cursor.execute(update_query, (status_update, message_id))

    select_query = f'''
            SELECT * FROM REPAIRS
            WHERE MESSAGE_ID = ?;
        '''

    cursor.execute(select_query, (message_id,))
    rows = cursor.fetchall()

    conn.commit()
    conn.close()

    if not rows:
        print("В БД відсутні записи для MESSAGE_ID:", message_id)
        return

    try:
        for row in rows:
            (
                ID, USER_ID, DATE, DATE_REPAIR, CITY, WORKER_PERSON, NAME_SCOOTER, TYPE_REPAIR, REPAIR, COMMENT,
                PHOTO_REPAIR, RESPONSIBLE_PERSON, RESPONSIBLE_PERSON_STATUS, CHAT_ID, THREAD_ID, MESSAGE_ID
            ) = row

        text = (f"СЛУЖБОВА 🔧РЕМОНТ🔧: {DATE}\n"
                f"МІСТО: {CITY}\n"
                f"ПРАЦІВНИК: {WORKER_PERSON}\n"
                f"НОМЕР САМОКАТУ: {NAME_SCOOTER}\n"
                f"ВИД РЕМОНТУ: {TYPE_REPAIR}\n"
                f"ДЕТАЛЬ\РЕМОНТ: {REPAIR}\n\n"
                f"ВІДПОВІДАЛЬНА ОСОБА\n"
                f"{RESPONSIBLE_PERSON} - {RESPONSIBLE_PERSON_STATUS}")

        await bot.edit_message_text(chat_id=CHAT_ID, message_id=MESSAGE_ID, text=text)
    except Exception as e:
        print("SHIT:" + str(e))

    try:
        if "👍" in temp_new_emoji_data and \
                RESPONSIBLE_PERSON_STATUS == "погоджено \U0001F44D":
            ready_text = "\U00002705СЛУЖБОВУ ОПРАЦЬОВАНО\U00002705\n" + text
            important = await bot.send_message(chat_id=CHAT_ID, message_thread_id=data.scooter_repairs_finish,
                                             text=ready_text)

            old_thread_id = important.message_thread_id
            old_message_id = important.message_id

            conn = sqlite3.connect('base_scooters.db')
            cursor = conn.cursor()
            update_query = f'''
                            UPDATE REPAIRS
                            SET THREAD_ID = ?, MESSAGE_ID = ?
                            WHERE MESSAGE_ID = ?;
                            '''

            cursor.execute(update_query, (old_thread_id, old_message_id, message_id))
            conn.commit()
            conn.close()

            new_chat_id = CHAT_ID
            new_message_id = MESSAGE_ID

            link = "https://t.me/c/2448053501/" + str(old_thread_id) + "/" + str(old_message_id)

            correct_datatime = datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
            new_text = "\U00002705СЛУЖБОВУ 🔧РЕМОНТ🔧 ОПРАЦЬОВАНО\U00002705" \
                       "\nМІСТО: " + str(CITY) + \
                       "\nПРАЦІВНИК: " + str(WORKER_PERSON) + \
                       "\nНОМЕР САМОКАТУ: " + str(NAME_SCOOTER) + \
                       "\nВИД РЕМОНТУ: " + str(TYPE_REPAIR) + \
                       "\nДЕТАЛЬ\РЕМОНТ: " + str(REPAIR) + \
                       "\n\nВІДПОВІДАЛЬНА ОСОБА\n" + \
                       "" + str(RESPONSIBLE_PERSON) + "-" + str(RESPONSIBLE_PERSON_STATUS) + \
                       "\n\nДАТА ОПРАЦЮВАННЯ: " + str(correct_datatime) + "\n" + link

            await bot.edit_message_text(chat_id=new_chat_id, message_id=new_message_id, text=new_text)

        elif "👎" in temp_new_emoji_data and \
                RESPONSIBLE_PERSON_STATUS == "відхилено \U0001F44E":
            del_text = "\U0001F6ABСЛУЖБОВУ ВІДХИЛЕНО\U0001F6AB\n" + text
            important = await bot.send_message(chat_id=CHAT_ID, message_thread_id=data.scooter_repairs_finish,
                                             text=del_text)

            old_thread_id = important.message_thread_id
            old_message_id = important.message_id

            conn = sqlite3.connect('base_scooters.db')
            cursor = conn.cursor()
            update_query = f'''
                            UPDATE REPAIRS
                            SET THREAD_ID = ?, MESSAGE_ID = ?
                            WHERE MESSAGE_ID = ?;
                            '''
            cursor.execute(update_query, (old_thread_id, old_message_id, message_id))
            conn.commit()
            conn.close()

            new_chat_id = CHAT_ID
            new_message_id = MESSAGE_ID

            link = "https://t.me/c/2448053501/" + str(old_thread_id) + "/" + str(old_message_id)

            correct_datatime = datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
            new_text = "\U0001F6ABСЛУЖБОВУ 🔧РЕМОНТ🔧 ВІДХИЛЕНО\U0001F6AB" \
                       "\nДАТА СЛУЖБОВОЇ: " + str(DATE) + \
                       "\nМІСТО: " + str(CITY) + \
                       "\nПРАЦІВНИК: " + str(WORKER_PERSON) + \
                       "\nНОМЕР САМОКАТУ: " + str(NAME_SCOOTER) + \
                       "\nВИД РЕМОНТУ: " + str(TYPE_REPAIR) + \
                       "\nДЕТАЛЬ\РЕМОНТ: " + str(REPAIR) + \
                       "\n\nВІДПОВІДАЛЬНА ОСОБА\n" + \
                       "" + str(RESPONSIBLE_PERSON) + "-" + str(RESPONSIBLE_PERSON_STATUS) + \
                       "\n\nДАТА ОПРАЦЮВАННЯ: " + str(correct_datatime) + "\n" + link

            await bot.edit_message_text(chat_id=new_chat_id, message_id=new_message_id, text=new_text)
    except Exception as e:
        print("ATENTION: " + str(e))



async def main():

    '''UKR = zoneinfo.ZoneInfo("Europe/Kiev")

    #scheduler = AsyncIOScheduler(timezone=UKR)
    #scheduler.add_job(func=send_document_to_user, trigger='cron', day_of_week='mon-fri', hour=8, minute=59)
    #scheduler.add_job(func=send_rating_to_user, trigger='cron', day_of_week='mon-fri', hour=9, minute=30)
    #scheduler.add_job(test.copy_excel_content, trigger='cron', day_of_week='mon-fri', hour=15, minute=43)
    scheduler.start()'''


    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as shit:
        print("ПОМИЛКА ВИКОНАННЯ ФАЙЛУ:", shit)

    except KeyboardInterrupt:
        print("Бот завершено вручну")


