import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import get_session, Booking, User
from keyboards import *
from filters import IsAdminFilter
from utils import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Создание роутеров
user_router = Router()
admin_router = Router()
admin_router.message.filter(IsAdminFilter())


# Состояния для FSM
class BookingStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_month = State()
    waiting_for_time = State()
    waiting_for_zone = State()
    waiting_for_table = State()
    waiting_for_guests = State()
    waiting_for_name = State()
    waiting_for_contact = State()
    waiting_for_confirm = State()


# Регистрация роутеров
dp.include_router(admin_router)  # СНАЧАЛА админский роутер!
dp.include_router(user_router)  # ПОТОМ пользовательский

# Декоратор для безопасной работы с состоянием FSM
from functools import wraps


def safe_state(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except KeyError as e:
            logger.error(f"KeyError in {func.__name__}: {e}")

            state = None
            for arg in args:
                if isinstance(arg, FSMContext):
                    state = arg
                    break
            else:
                for value in kwargs.values():
                    if isinstance(value, FSMContext):
                        state = value
                        break

            if state:
                await state.clear()

            message = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    message = arg
                    break

            if message:
                if isinstance(message, CallbackQuery):
                    await message.message.answer(
                        "⚠️ Произошла ошибка. Пожалуйста, начните бронирование заново.",
                        reply_markup=get_main_menu()
                    )
                else:
                    await message.answer(
                        "⚠️ Произошла ошибка. Пожалуйста, начните бронирование заново.",
                        reply_markup=get_main_menu()
                    )

    return wrapper


# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ==========

@user_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    # Регистрация пользователя
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == message.from_user.id).first()
        if not user:
            user = User(
                user_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            session.add(user)
            session.commit()
    finally:
        session.close()

    await message.answer(
        "🎉 Добро пожаловать в систему бронирования столиков!\n\n"
        "Выберите действие в меню:",
        reply_markup=get_main_menu()
    )


@user_router.message(Command("myid"))
async def cmd_myid(message: Message):
    """Показать ID пользователя (для добавления в админы)"""
    await message.answer(
        f"👤 Ваш ID: <code>{message.from_user.id}</code>\n"
        f"👤 Username: @{message.from_user.username}\n\n"
        "Добавьте этот ID в файл .env в переменную ADMIN_IDS",
        parse_mode="HTML"
    )


@user_router.message(F.text == "📅 Забронировать столик")
async def start_booking(message: Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_date)

    # Получаем информацию о текущем и следующем месяце
    today = datetime.now()

    # Русские названия месяцев
    month_names = {
        1: "январь", 2: "февраль", 3: "март", 4: "апрель",
        5: "май", 6: "июнь", 7: "июль", 8: "август",
        9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
    }

    current_month = month_names[today.month]
    current_year = today.year

    # Определяем следующий месяц
    if today.month == 12:
        next_month_name = month_names[1]
        next_month_year = today.year + 1
    else:
        next_month_name = month_names[today.month + 1]
        next_month_year = today.year

    await message.answer(
        f"📅 <b>Выберите дату бронирования</b>\n\n"
        f"<i>Вы можете выбрать дату из текущего месяца ({current_month} {current_year}) "
        f"или следующего месяца ({next_month_name} {next_month_year})</i>\n\n"
        f"Бронирование возможно максимум на 30 дней вперед.\n"
        f"Сегодня: {today.strftime('%d.%m.%Y')}",
        parse_mode="HTML",
        reply_markup=get_date_selection()
    )


@user_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего процесса бронирования"""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("Нет активного процесса для отмены.")
        return

    await state.clear()
    await message.answer(
        "❌ Процесс бронирования отменен.",
        reply_markup=get_main_menu()
    )


@user_router.message(Command("help"))
async def cmd_help(message: Message):
    """Показать справку"""
    help_text = (
        "📖 <b>Справка по боту бронирования</b>\n\n"
        "👤 <b>Для пользователей:</b>\n"
        "/start - Начать работу с ботом\n"
        "/cancel - Отменить текущее бронирование\n"
        "/myid - Показать мой ID\n"
        "/help - Показать эту справку\n\n"
        "👨‍💼 <b>Для администраторов:</b>\n"
        "/admin - Открыть панель администратора\n\n"
        "📞 Если возникли проблемы, свяжитесь с администратором."
    )

    await message.answer(help_text, parse_mode="HTML")


@user_router.callback_query(F.data == "back_to_date_selection")
async def back_to_date_selection(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    await state.set_state(BookingStates.waiting_for_date)

    today = datetime.now()

    # Русские названия месяцев
    month_names = {
        1: "январь", 2: "февраль", 3: "март", 4: "апрель",
        5: "май", 6: "июнь", 7: "июль", 8: "август",
        9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
    }

    current_month = month_names[today.month]
    current_year = today.year

    if today.month == 12:
        next_month_name = month_names[1]
        next_month_year = today.year + 1
    else:
        next_month_name = month_names[today.month + 1]
        next_month_year = today.year

    await callback.message.edit_text(
        f"📅 <b>Выберите дату бронирования</b>\n\n"
        f"<i>Вы можете выбрать дату из текущего месяца ({current_month} {current_year}) "
        f"или следующего месяца ({next_month_name} {next_month_year})</i>\n\n"
        f"Бронирование возможно максимум на 30 дней вперед.\n"
        f"Сегодня: {today.strftime('%d.%m.%Y')}",
        parse_mode="HTML",
        reply_markup=get_date_selection()
    )


@user_router.callback_query(F.data.startswith("date_"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]

    valid, msg = validate_date(date_str)
    if not valid:
        await callback.answer(msg, show_alert=True)
        return

    await state.update_data(date=date_str)
    await state.set_state(BookingStates.waiting_for_zone)

    # Форматируем дату для отображения
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')

    await callback.message.edit_text(f"📅 Выбрана дата: <b>{formatted_date}</b>")
    await callback.message.answer("🎯 Выберите зону:", reply_markup=get_zones_keyboard())


@user_router.callback_query(F.data == "select_month")
async def select_month(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_month)
    await callback.message.edit_text("📅 Выберите месяц:", reply_markup=DateKeyboard.get_months_keyboard())


@user_router.callback_query(F.data.startswith("month_"))
async def process_month(callback: CallbackQuery, state: FSMContext):
    month_key = callback.data.split("_")[1]
    days_keyboard = DateKeyboard.get_days_for_month(month_key)

    if days_keyboard:
        # Получаем название месяца для заголовка
        year, month_num = map(int, month_key.split('-'))
        month_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        month_name = month_names.get(month_num, month_key)

        await callback.message.edit_text(
            f"📅 <b>Выберите день</b>\n"
            f"<i>{month_name} {year}</i>",
            parse_mode="HTML",
            reply_markup=days_keyboard
        )
    else:
        await callback.answer("Нет доступных дат в этом месяце", show_alert=True)


@user_router.callback_query(F.data.startswith("zone_"))
@safe_state
async def process_zone(callback: CallbackQuery, state: FSMContext):
    zone = callback.data.split("_")[1]

    # Получаем данные и проверяем наличие даты
    data = await state.get_data()
    if 'date' not in data:
        await callback.answer("❌ Сначала выберите дату.", show_alert=True)
        await state.clear()
        await callback.message.answer(
            "Произошла ошибка. Начните бронирование заново.",
            reply_markup=get_main_menu()
        )
        return

    await state.update_data(zone=zone)

    zone_name = config.ZONES.get(zone, zone)
    await callback.message.edit_text(f"🎯 Выбрана зона: <b>{zone_name}</b>")

    await state.set_state(BookingStates.waiting_for_time)
    await callback.message.answer(
        f"⏰ Выберите время для {zone_name}:\n"
        f"Мы работаем с {config.OPEN_TIME}:00 до {config.CLOSE_TIME}:00",
        reply_markup=get_time_slots(data['date'], zone)
    )


@user_router.callback_query(F.data.startswith("time_"))
@safe_state
async def process_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[1]

    valid, msg = validate_time(time_str)
    if not valid:
        await callback.answer(msg, show_alert=True)
        return

    # Получаем данные с проверкой
    data = await state.get_data()

    if 'date' not in data or 'zone' not in data:
        await callback.answer("❌ Сначала выберите дату и зону.", show_alert=True)
        await state.clear()
        await callback.message.answer(
            "Произошла ошибка. Начните бронирование заново.",
            reply_markup=get_main_menu()
        )
        return

    date = data['date']
    zone = data['zone']

    # Проверяем доступные столики
    available_tables = get_available_tables(date, time_str, zone)

    if not available_tables:
        await callback.answer("❌ На это время все столики заняты. Выберите другое время.", show_alert=True)
        return

    await state.update_data(time=time_str)
    await callback.message.edit_text(f"⏰ Выбрано время: <b>{time_str}</b>")

    await state.set_state(BookingStates.waiting_for_table)
    await callback.message.answer(
        f"🪑 <b>Выберите свободный столик:</b>\n"
        f"Дата: {date}\n"
        f"Время: {time_str}",
        parse_mode="HTML",
        reply_markup=get_tables_keyboard(date, time_str, zone)
    )


@user_router.callback_query(F.data == "no_tables")
async def no_tables_available(callback: CallbackQuery):
    await callback.answer("На это время нет свободных столиков. Выберите другое время.", show_alert=True)


@user_router.callback_query(F.data.startswith("table_"))
@safe_state
async def process_table(callback: CallbackQuery, state: FSMContext):
    table_num = int(callback.data.split("_")[1])

    # Получаем данные с проверкой
    data = await state.get_data()

    # Проверяем наличие всех необходимых данных
    required_keys = ['date', 'time', 'zone']
    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        await callback.answer(
            f"❌ Ошибка: отсутствуют данные ({', '.join(missing_keys)}). Начните заново.",
            show_alert=True
        )
        await state.clear()
        await callback.message.answer(
            "Произошла ошибка. Пожалуйста, начните бронирование заново.",
            reply_markup=get_main_menu()
        )
        return

    date = data['date']
    time = data['time']
    zone = data['zone']

    # Проверяем, что столик все еще свободен
    available_tables = get_available_tables(date, time, zone)
    if table_num not in available_tables:
        await callback.answer("❌ Этот столик уже занят. Выберите другой.", show_alert=True)
        return

    await state.update_data(table_number=table_num)
    await callback.message.edit_text(f"🪑 Выбран столик: <b>№{table_num}</b>")

    await state.set_state(BookingStates.waiting_for_guests)
    await callback.message.answer(
        "👥 Сколько гостей будет?",
        reply_markup=get_guests_keyboard()
    )


@user_router.callback_query(F.data.startswith("guests_"))
async def process_guests(callback: CallbackQuery, state: FSMContext):
    guests = int(callback.data.split("_")[1])
    await state.update_data(guests=guests)

    await callback.message.edit_text(f"👥 Количество гостей: <b>{guests}</b>")

    await state.set_state(BookingStates.waiting_for_name)
    await callback.message.answer(
        "👤 Пожалуйста, введите ваше имя для бронирования:",
        reply_markup=get_name_input_keyboard()
    )


@user_router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if not name or len(name) < 2:
        await message.answer("❌ Пожалуйста, введите корректное имя (минимум 2 символа)")
        return

    await state.update_data(full_name=name)

    await state.set_state(BookingStates.waiting_for_contact)
    await message.answer(
        f"👤 Имя сохранено: <b>{name}</b>\n\n"
        "📱 Теперь поделитесь своим номером телефона для связи:",
        parse_mode="HTML",
        reply_markup=get_contact_keyboard()
    )


@user_router.message(BookingStates.waiting_for_contact, F.contact)
async def process_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    await state.update_data(phone=phone)

    # Сохраняем телефон в профиль пользователя
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == message.from_user.id).first()
        if user:
            user.phone = phone
            session.commit()
    finally:
        session.close()

    data = await state.get_data()
    booking_summary = format_booking_data(data)

    await state.set_state(BookingStates.waiting_for_confirm)

    await message.answer(
        f"📋 <b>Подтвердите бронирование:</b>\n\n{booking_summary}",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )


@user_router.message(BookingStates.waiting_for_contact, F.text)
async def process_contact_text(message: Message, state: FSMContext):
    """Обработка текстового ввода телефона"""
    phone = message.text.strip()

    # Простая валидация номера телефона
    cleaned_phone = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not cleaned_phone.isdigit() or len(cleaned_phone) < 10:
        await message.answer("❌ Пожалуйста, введите корректный номер телефона или поделитесь контактом.")
        return

    await state.update_data(phone=phone)

    # Сохраняем телефон в профиль пользователя
    session = get_session()
    try:
        user = session.query(User).filter(User.user_id == message.from_user.id).first()
        if user:
            user.phone = phone
            session.commit()
    finally:
        session.close()

    data = await state.get_data()
    booking_summary = format_booking_data(data)

    await state.set_state(BookingStates.waiting_for_confirm)

    await message.answer(
        f"📋 <b>Подтвердите бронирование:</b>\n\n{booking_summary}",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )


@user_router.callback_query(F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Сохраняем бронирование в БД
    session = get_session()
    try:
        booking = Booking(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=data['full_name'],
            phone=data['phone'],
            zone=data['zone'],
            table_number=data['table_number'],
            date=data['date'],
            time=data['time'],
            guests=data['guests'],
            status='pending'
        )
        session.add(booking)
        session.commit()

        booking_summary = format_booking_data(data)

        # Уведомляем администраторов
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"📥 <b>Новая заявка на бронирование!</b>\n\n"
                    f"{booking_summary}\n\n"
                    f"ID брони: {booking.id}",
                    parse_mode="HTML",
                    reply_markup=get_booking_actions(booking.id)
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")

        await callback.message.edit_text(
            f"✅ <b>Заявка на бронирование отправлена!</b>\n\n"
            f"{booking_summary}\n\n"
            f"Статус: <b>на рассмотрении</b>\n"
            f"Ожидайте подтверждения от администратора.",
            parse_mode="HTML"
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при сохранении бронирования: {e}")
        await callback.message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")
    finally:
        session.close()


@user_router.message(F.text == "📋 Мои бронирования")
async def show_my_bookings(message: Message):
    session = get_session()
    try:
        bookings = session.query(Booking).filter(
            Booking.user_id == message.from_user.id
        ).order_by(Booking.date, Booking.time).all()

        if not bookings:
            await message.answer("У вас нет активных бронирований.")
            return

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML"
            )
    finally:
        session.close()


@user_router.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
    await message.answer(
        "📞 <b>Контакты:</b>\n\n"
        "🏢 Наш адрес: ул. Примерная, 123\n"
        "📱 Телефон: +7 (XXX) XXX-XX-XX\n"
        "🕒 Часы работы: 12:00 - 23:00\n\n"
        "📍 Зоны отдыха:\n"
        "• Тихий зал (столики 1-5)\n"
        "• Караоке зал (столики 6-10)",
        parse_mode="HTML"
    )


@user_router.callback_query(F.data == "cancel_booking")
async def cancel_booking_user(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Бронирование отменено.")
    await callback.message.answer(
        "Выберите действие в меню:",
        reply_markup=get_main_menu()
    )


# ========== АДМИН КОМАНДЫ ==========

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    logger.info(f"Admin command from user {message.from_user.id}")
    logger.info(f"Config ADMIN_IDS: {config.ADMIN_IDS}")

    await message.answer(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        f"Ваш ID: <code>{message.from_user.id}</code>\n"
        f"Админ ID из настроек: {config.ADMIN_IDS}\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )


@admin_router.message(F.text == "📊 Все бронирования")
async def show_all_bookings(message: Message):
    session = get_session()
    try:
        bookings = session.query(Booking).order_by(
            Booking.date, Booking.time
        ).all()

        if not bookings:
            await message.answer("Нет активных бронирований.")
            return

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML",
                reply_markup=get_booking_actions(booking.id)
            )
    finally:
        session.close()


@admin_router.message(F.text == "⏳ Ожидают подтверждения")
async def show_pending_bookings(message: Message):
    session = get_session()
    try:
        bookings = session.query(Booking).filter(
            Booking.status == 'pending'
        ).order_by(Booking.created_at).all()

        if not bookings:
            await message.answer("Нет бронирований, ожидающих подтверждения.")
            return

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML",
                reply_markup=get_booking_actions(booking.id)
            )
    finally:
        session.close()


@admin_router.message(F.text == "📅 Бронирования на сегодня")
async def show_today_bookings(message: Message):
    today = datetime.now().strftime('%Y-%m-%d')
    session = get_session()
    try:
        bookings = session.query(Booking).filter(
            Booking.date == today,
            Booking.status.in_(['pending', 'confirmed'])
        ).order_by(Booking.time).all()

        if not bookings:
            await message.answer("На сегодня нет бронирований.")
            return

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML",
                reply_markup=get_booking_actions(booking.id)
            )
    finally:
        session.close()


@admin_router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[-1])

    session = get_session()
    try:
        booking = session.query(Booking).get(booking_id)
        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        booking.status = 'confirmed'
        session.commit()

        # Уведомляем пользователя
        try:
            await bot.send_message(
                booking.user_id,
                f"✅ <b>Ваша бронь подтверждена!</b>\n\n"
                f"{format_booking_data(booking)}\n\n"
                f"Ждем вас {booking.date} в {booking.time}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")

        await callback.message.edit_text(
            format_booking(booking),
            parse_mode="HTML",
            reply_markup=get_booking_actions(booking.id)
        )
        await callback.answer("Бронь подтверждена", show_alert=True)

    finally:
        session.close()


@admin_router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[-1])

    session = get_session()
    try:
        booking = session.query(Booking).get(booking_id)
        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        booking.status = 'cancelled'
        session.commit()

        # Уведомляем пользователя
        try:
            await bot.send_message(
                booking.user_id,
                f"❌ <b>Ваша бронь отменена администратором</b>\n\n"
                f"{format_booking_data(booking)}\n\n"
                f"По вопросам обращайтесь к администратору.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")

        await callback.message.edit_text(
            format_booking(booking),
            parse_mode="HTML",
            reply_markup=get_booking_actions(booking.id)
        )
        await callback.answer("Бронь отменена", show_alert=True)

    finally:
        session.close()


@admin_router.callback_query(F.data.startswith("admin_delete_"))
async def admin_delete_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[-1])

    session = get_session()
    try:
        booking = session.query(Booking).get(booking_id)
        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        session.delete(booking)
        session.commit()

        await callback.message.delete()
        await callback.answer("Бронь удалена", show_alert=True)

    finally:
        session.close()


@admin_router.callback_query(F.data.startswith("admin_edit_time_"))
async def admin_edit_time(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[-1])
    await callback.answer("Функция изменения времени пока не реализована", show_alert=True)


@admin_router.message(F.text == "↩️ Назад в меню")
async def back_to_menu(message: Message):
    await message.answer(
        "Возвращаюсь в главное меню:",
        reply_markup=get_main_menu()
    )


# Обработчик для любых текстовых сообщений вне состояний
@user_router.message()
async def handle_other_messages(message: Message, state: FSMContext):
    """Обработчик для всех остальных сообщений"""
    current_state = await state.get_state()

    # Если пользователь в каком-то состоянии, просим выполнить текущий шаг
    if current_state:
        state_name = current_state.split(":")[-1]
        state_messages = {
            "waiting_for_date": "📅 Пожалуйста, выберите дату из предложенных вариантов",
            "waiting_for_month": "📅 Выберите месяц из предложенных вариантов",
            "waiting_for_time": "⏰ Выберите время из предложенных вариантов",
            "waiting_for_zone": "🎯 Выберите зону из предложенных вариантов",
            "waiting_for_table": "🪑 Выберите столик из предложенных вариантов",
            "waiting_for_guests": "👥 Выберите количество гостей",
            "waiting_for_name": "👤 Пожалуйста, введите ваше имя для бронирования",
            "waiting_for_contact": "📱 Пожалуйста, поделитесь номером телефона или введите его вручную",
            "waiting_for_confirm": "📋 Подтвердите или отмените бронирование"
        }

        if state_name in state_messages:
            await message.answer(state_messages[state_name])
        else:
            await message.answer("Пожалуйста, используйте кнопки меню для навигации.")
    else:
        # Если не в состоянии, показываем главное меню
        await message.answer(
            "Используйте кнопки меню для навигации:",
            reply_markup=get_main_menu()
        )


async def main():
    # Создаем директорию для данных, если её нет
    import os
    if not os.path.exists('data'):
        os.makedirs('data')

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())