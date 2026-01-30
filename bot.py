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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    waiting_for_time = State()
    waiting_for_table = State()
    waiting_for_guests = State()
    waiting_for_name = State()
    waiting_for_contact = State()
    waiting_for_confirm = State()


# Регистрация роутеров
dp.include_router(admin_router)
dp.include_router(user_router)


# ========== ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========







# В класс StatesGroup добавьте (если нужно):
class AdminStates(StatesGroup):
    waiting_for_confirm_outdated = State()
    waiting_for_confirm_cancelled = State()


# Обновите обработчики с подтверждением:

@admin_router.message(F.text == "🗑️ Удалить неактуальные")
async def confirm_delete_outdated(message: Message, state: FSMContext):
    """Подтверждение удаления неактуальных бронирований"""
    session = get_session()
    try:
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')

        # Считаем количество
        outdated_count = session.query(Booking).filter(
            (Booking.date < today) |
            ((Booking.date == today) & (Booking.time < current_time))
        ).count()

        if outdated_count == 0:
            await message.answer(
                "✅ <b>Нет неактуальных (прошедших) бронирований.</b>",
                parse_mode="HTML"
            )
            return

        await state.set_state(AdminStates.waiting_for_confirm_outdated)
        await state.update_data(outdated_count=outdated_count)

        await message.answer(
            f"⚠️ <b>Подтвердите удаление {outdated_count} неактуальных бронирований:</b>\n\n"
            f"🗑️ <b>Будут удалены:</b>\n"
            f"• Бронирования с прошедшей датой\n"
            f"• Бронирования с прошедшим временем сегодня\n\n"
            f"<i>Статусы: pending, confirmed, cancelled</i>\n\n"
            f"<b>Для подтверждения нажмите:</b>\n"
            f"✅ <code>Удалить {outdated_count} неактуальных</code>\n\n"
            f"<i>Или отправьте любую другую команду для отмены.</i>",
            parse_mode="HTML"
        )

    finally:
        session.close()


@admin_router.message(AdminStates.waiting_for_confirm_outdated)
async def execute_delete_outdated(message: Message, state: FSMContext):
    """Выполнение удаления неактуальных бронирований"""
    if f"Удалить" in message.text:
        data = await state.get_data()
        outdated_count = data.get('outdated_count', 0)

        session = get_session()
        try:
            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M')

            # Удаляем
            deleted = session.query(Booking).filter(
                (Booking.date < today) |
                ((Booking.date == today) & (Booking.time < current_time))
            ).delete()

            session.commit()

            await message.answer(
                f"✅ <b>Удалено {deleted} неактуальных бронирований.</b>",
                parse_mode="HTML"
            )

            logger.info(f"Админ {message.from_user.id} удалил {deleted} неактуальных бронирований")

        except Exception as e:
            logger.error(f"Ошибка при удалении неактуальных бронирований: {e}")
            await message.answer(
                "❌ <b>Произошла ошибка при удалении.</b>",
                parse_mode="HTML"
            )
        finally:
            session.close()
    else:
        await message.answer(
            "❌ <b>Удаление отменено.</b>",
            parse_mode="HTML"
        )

    await state.clear()

async def show_welcome_message(message: Message, state: FSMContext = None):
    """Показать приветственное сообщение"""
    if state:
        await state.clear()

    welcome_text = (
        f"🍽️ <b>Добро пожаловать в {config.RESTAURANT_NAME}!</b>\n\n"
        "Мы рады приветствовать вас в нашей системе бронирования столиков. "
        "Здесь вы можете легко и быстро забронировать столик для приятного вечера.\n\n"
        "<b>📋 Доступные функции:</b>\n"
        "• 🎯 Забронировать столик онлайн\n"
        "• 📋 Просмотреть свои бронирования\n"
        "• ℹ️ Узнать о нас больше\n"
        "• 📞 Связаться с нами\n\n"
        "<i>Начните с кнопки '🎯 Забронировать столик' или выберите другое действие в меню.</i>"
    )

    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu())


# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ==========

@user_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start - начало работы с ботом"""
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
            logger.info(f"Зарегистрирован новый пользователь: {message.from_user.id}")
    finally:
        session.close()

    await show_welcome_message(message, state)


@user_router.message(Command("myid"))
async def cmd_myid(message: Message):
    """Показать ID пользователя"""
    await message.answer(
        f"👤 <b>Ваши данные:</b>\n\n"
        f"🆔 Ваш ID: <code>{message.from_user.id}</code>\n"
        f"👤 Username: @{message.from_user.username or 'не указан'}\n"
        f"📛 Имя: {message.from_user.full_name or 'не указано'}\n\n"
        f"<i>Этот ID нужен администратору для предоставления прав.</i>",
        parse_mode="HTML"
    )


@user_router.message(Command("cancel"))
@user_router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего процесса бронирования"""
    current_state = await state.get_state()

    if current_state:
        await state.clear()
        await message.answer(
            "❌ <b>Процесс бронирования отменен.</b>\n\n"
            "Вы можете начать заново в любое время.",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer("Нет активного процесса для отмены.")


@user_router.message(Command("help"))
@user_router.message(F.text == "🆘 Помощь")
async def cmd_help(message: Message):
    """Показать справку"""
    help_text = (
        "🆘 <b>Справка по боту бронирования</b>\n\n"

        "👤 <b>Для пользователей:</b>\n"
        "/start - Начать работу с ботом\n"
        "/myid - Показать мой ID\n"
        "/cancel - Отменить текущее бронирование\n"
        "/help - Показать эту справку\n\n"

        "🎯 <b>Процесс бронирования:</b>\n"
        "1. Выберите дату\n"
        "2. Выберите удобное время\n"
        "3. Выберите свободный столик\n"
        "4. Укажите количество гостей\n"
        "5. Введите ваше имя\n"
        "6. Укажите контактный телефон\n"
        "7. Подтвердите бронирование\n\n"

        "👨‍💼 <b>Для администраторов:</b>\n"
        "/admin - Открыть панель администратора\n\n"

        "📞 <b>Если возникли проблемы:</b>\n"
        f"• Используйте кнопку '📞 Контакты'\n"
        f"• Или свяжитесь по телефону: {config.RESTAURANT_PHONE}\n\n"

        f"<i>Бот работает с {config.OPEN_TIME_STR} до {config.CLOSE_TIME_STR} ежедневно.</i>"
    )

    await message.answer(help_text, parse_mode="HTML")


@user_router.message(F.text == "🎯 Забронировать столик")
async def start_booking(message: Message, state: FSMContext):
    """Начать процесс бронирования"""
    await state.set_state(BookingStates.waiting_for_date)

    today = datetime.now()
    formatted_today = today.strftime('%d.%m.%Y')

    # Проверяем, можно ли сегодня бронировать
    now = datetime.now()
    now_in_minutes = now.hour * 60 + now.minute

    if now_in_minutes > config.LAST_BOOKING_TIME_MINUTES:
        await message.answer(
            f"❌ <b>Бронирование на сегодня завершено</b>\n\n"
            f"Мы работаем до {config.CLOSE_TIME_STR}. "
            f"Последняя бронь возможна до {config.LAST_BOOKING_TIME_STR}.\n\n"
            f"Пожалуйста, выберите дату начиная с завтрашнего дня.",
            parse_mode="HTML",
            reply_markup=get_date_selection()
        )
    else:
        await message.answer(
            f"🎯 <b>Начнем бронирование!</b>\n\n"
            f"<i>Выберите дату для вашего визита:</i>\n\n"
            f"📅 Сегодня: {formatted_today}\n"
            f"⏰ Часы работы: {config.WORKING_HOURS_STR}\n"
            f"🕒 Последняя бронь: {config.LAST_BOOKING_TIME_STR}\n"
            f"🪑 Всего столиков: {len(config.TABLES['main'])}\n\n"
            f"<i>Выберите дату из списка ниже:</i>",
            parse_mode="HTML",
            reply_markup=get_date_selection()
        )


@user_router.message(F.text == "📋 Мои бронирования")
async def show_my_bookings(message: Message):
    """Показать все бронирования пользователя"""
    session = get_session()
    try:
        # Получаем текущие бронирования
        today = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M')

        future_bookings = session.query(Booking).filter(
            Booking.user_id == message.from_user.id,
            Booking.status.in_(['pending', 'confirmed']),
            (Booking.date > today) |
            ((Booking.date == today) & (Booking.time > current_time))
        ).order_by(Booking.date, Booking.time).all()

        # Получаем прошедшие бронирования
        past_bookings = session.query(Booking).filter(
            Booking.user_id == message.from_user.id,
            Booking.status.in_(['pending', 'confirmed']),
            (Booking.date < today) |
            ((Booking.date == today) & (Booking.time <= current_time))
        ).order_by(Booking.date.desc(), Booking.time.desc()).all()

        if not future_bookings and not past_bookings:
            await message.answer(
                "📋 <b>У вас еще нет бронирований</b>\n\n"
                "Нажмите '🎯 Забронировать столик', чтобы создать первую бронь!",
                parse_mode="HTML"
            )
            return

        if future_bookings:
            await message.answer(
                "📋 <b>Ваши будущие бронирования:</b>",
                parse_mode="HTML"
            )
            for booking in future_bookings:
                await message.answer(
                    format_booking(booking),
                    parse_mode="HTML"
                )

        if past_bookings:
            await message.answer(
                "📜 <b>Ваши прошлые бронирования:</b>",
                parse_mode="HTML"
            )
            for booking in past_bookings[:5]:  # Показываем только 5 последних
                await message.answer(
                    format_booking(booking),
                    parse_mode="HTML"
                )

    finally:
        session.close()


@user_router.message(F.text == "ℹ️ О нас")
async def show_about(message: Message):
    """Показать информацию о ресторане"""
    about_text = (
        f"🍽️ <b>{config.RESTAURANT_NAME}</b>\n\n"

        f"<b>О нашем заведении:</b>\n"
        f"{config.restaurant_config['about']['description']}\n\n"

        f"<b>📋 Особенности:</b>\n"
    )

    # Добавляем особенности
    for feature in config.restaurant_config['about']['features']:
        about_text += f"{feature}\n"

    about_text += (
        f"\n<b>⏰ Часы работы:</b>\n"
        f"Ежедневно с {config.OPEN_TIME_STR} до {config.CLOSE_TIME_STR}\n\n"

        f"<i>Ждем вас в гости! Для бронирования нажмите '🎯 Забронировать столик'.</i>"
    )

    await message.answer(about_text, parse_mode="HTML")


@user_router.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
    """Показать контактную информацию"""
    contacts_text = (
        "📞 <b>Контакты</b>\n\n"

        f"🏢 <b>{config.RESTAURANT_NAME}</b>\n"
        f"📍 Адрес: {config.RESTAURANT_ADDRESS}\n"
        f"📱 Телефон: {config.RESTAURANT_PHONE}\n"
        f"⏰ Часы работы: {config.WORKING_HOURS_STR}\n\n"

        "<b>🗺️ Как добраться:</b>\n"
        f"• 🚇 Метро: {config.restaurant_config['location']['metro']}\n"
        f"• 🚌 Автобусы: {config.restaurant_config['location']['buses']}\n"
        f"• 🚗 Парковка: {config.restaurant_config['location']['parking']}\n\n"

        "<b>📱 Социальные сети:</b>\n"
        f"• Instagram: {config.restaurant_config['social_media']['instagram']}\n"
        f"• VK: {config.restaurant_config['social_media']['vk']}\n"
        f"• Telegram: {config.restaurant_config['social_media']['telegram']}\n\n"

        "<i>Для бронирования столика нажмите '🎯 Забронировать столик'.</i>"
    )

    await message.answer(contacts_text, parse_mode="HTML")


# ========== ОБРАБОТЧИКИ КОЛЛБЭКОВ БРОНИРОВАНИЯ ==========

@user_router.callback_query(F.data == "back_to_date_selection")
async def back_to_date_selection(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    await state.set_state(BookingStates.waiting_for_date)
    await callback.message.edit_text(
        "📅 <b>Выберите дату для бронирования:</b>",
        parse_mode="HTML",
        reply_markup=get_date_selection()
    )
    await callback.answer()


@user_router.callback_query(F.data.startswith("date_"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    date_str = callback.data.split("_")[1]

    valid, msg = validate_date(date_str)
    if not valid:
        await callback.answer(msg, show_alert=True)
        return

    await state.update_data(date=date_str, zone='main')
    await state.set_state(BookingStates.waiting_for_time)

    # Форматируем дату для отображения
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')

    # Определяем день недели
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[date_obj.weekday()]

    await callback.message.edit_text(
        f"✅ <b>Дата выбрана:</b> {formatted_date} ({day_name})\n\n"
        f"<i>Теперь выберите удобное время:</i>",
        parse_mode="HTML",
        reply_markup=get_back_to_dates_keyboard()
    )

    # Показываем доступные временные слоты
    await callback.message.answer(
        f"⏰ <b>Выберите время на {formatted_date}:</b>",
        parse_mode="HTML",
        reply_markup=get_time_slots(date_str, 'main')
    )

    await callback.answer()


@user_router.callback_query(F.data.startswith("time_"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    time_str = callback.data.split("_")[1]

    data = await state.get_data()

    if 'date' not in data:
        await callback.answer("❌ Сначала выберите дату.", show_alert=True)
        await state.clear()
        await callback.message.answer(
            "Произошла ошибка. Начните бронирование заново.",
            reply_markup=get_main_menu()
        )
        return

    date = data['date']
    zone = 'main'

    # Проверяем доступные столики
    available_tables = get_available_tables(date, time_str, zone)

    if not available_tables:
        await callback.answer("❌ На это время все столики заняты. Выберите другое время.", show_alert=True)
        return

    await state.update_data(time=time_str)
    await state.set_state(BookingStates.waiting_for_table)

    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')

    await callback.message.edit_text(
        f"✅ <b>Время выбрано:</b> {time_str}\n"
        f"📅 Дата: {formatted_date}\n\n"
        f"<i>Свободных столиков: {len(available_tables)} из {len(config.TABLES['main'])}</i>",
        parse_mode="HTML",
        reply_markup=get_back_to_times_keyboard()
    )

    await callback.message.answer(
        f"🪑 <b>Выберите столик на {formatted_date} в {time_str}:</b>",
        parse_mode="HTML",
        reply_markup=get_tables_keyboard(date, time_str, zone)
    )

    await callback.answer()


@user_router.callback_query(F.data == "no_tables")
async def no_tables_available(callback: CallbackQuery):
    """Обработка отсутствия свободных столиков"""
    await callback.answer(
        "❌ Нет свободных столиков на это время. "
        "Пожалуйста, выберите другое время.",
        show_alert=True
    )


@user_router.callback_query(F.data.startswith("table_"))
async def process_table(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора столика"""
    table_num = int(callback.data.split("_")[1])

    data = await state.get_data()

    if 'date' not in data or 'time' not in data:
        await callback.answer("❌ Сначала выберите дату и время.", show_alert=True)
        await state.clear()
        await callback.message.answer(
            "Произошла ошибка. Начните бронирование заново.",
            reply_markup=get_main_menu()
        )
        return

    date = data['date']
    time = data['time']
    zone = 'main'

    # Проверяем, что столик все еще свободен
    available_tables = get_available_tables(date, time, zone)
    if table_num not in available_tables:
        await callback.answer("❌ Этот столик уже занят. Выберите другой.", show_alert=True)
        return

    await state.update_data(table_number=table_num)
    await state.set_state(BookingStates.waiting_for_guests)

    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')

    await callback.message.edit_text(
        f"✅ <b>Столик выбран:</b> №{table_num}\n"
        f"📅 Дата: {formatted_date}\n"
        f"⏰ Время: {time}\n\n"
        f"<i>Отлично! Теперь укажите количество гостей:</i>",
        parse_mode="HTML",
        reply_markup=get_back_to_tables_keyboard()
    )

    await callback.message.answer(
        "👥 <b>Сколько гостей будет?</b>\n\n"
        "<i>Выберите подходящий вариант:</i>",
        parse_mode="HTML",
        reply_markup=get_guests_keyboard()
    )

    await callback.answer()


@user_router.callback_query(F.data == "back_to_time_selection")
async def back_to_time_selection(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору времени"""
    await state.set_state(BookingStates.waiting_for_time)

    data = await state.get_data()
    if 'date' in data:
        date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')

        await callback.message.edit_text(
            f"⏰ <b>Выберите время на {formatted_date}:</b>",
            parse_mode="HTML",
            reply_markup=get_time_slots(data['date'], 'main')
        )

    await callback.answer()


@user_router.callback_query(F.data.startswith("guests_"))
async def process_guests(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора количества гостей"""
    guests_data = callback.data.split("_")[1]

    if guests_data == "more":
        # Показать клавиатуру для выбора точного количества
        await callback.message.edit_text(
            "👨‍👩‍👧‍👦 <b>Выберите точное количество гостей:</b>",
            parse_mode="HTML",
            reply_markup=get_more_guests_keyboard()
        )
        await callback.answer()
        return

    guests = int(guests_data)
    await state.update_data(guests=guests)
    await state.set_state(BookingStates.waiting_for_name)

    await callback.message.edit_text(
        f"✅ <b>Количество гостей:</b> {guests}\n\n"
        f"<i>Отлично! Теперь введите ваше имя:</i>",
        parse_mode="HTML",
        reply_markup=get_back_to_guests_keyboard()
    )

    await callback.message.answer(
        "👤 <b>Введите ваше имя для бронирования:</b>\n\n"
        "<i>Пример: Иван Иванов</i>",
        parse_mode="HTML",
        reply_markup=get_name_input_keyboard()
    )

    await callback.answer()


@user_router.callback_query(F.data == "back_to_guests")
async def back_to_guests(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору количества гостей"""
    await state.set_state(BookingStates.waiting_for_guests)

    await callback.message.edit_text(
        "👥 <b>Сколько гостей будет?</b>\n\n"
        "<i>Выберите подходящий вариант:</i>",
        parse_mode="HTML",
        reply_markup=get_guests_keyboard()
    )

    await callback.answer()


@user_router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    name = message.text.strip()

    if not name or len(name) < 2:
        await message.answer(
            "❌ <b>Имя должно содержать минимум 2 символа.</b>\n\n"
            "Пожалуйста, введите ваше имя еще раз:",
            parse_mode="HTML"
        )
        return

    if len(name) > 50:
        await message.answer(
            "❌ <b>Имя слишком длинное.</b>\n\n"
            "Пожалуйста, введите имя короче (максимум 50 символов):",
            parse_mode="HTML"
        )
        return

    await state.update_data(full_name=name)
    await state.set_state(BookingStates.waiting_for_contact)

    await message.answer(
        f"✅ <b>Имя сохранено:</b> {name}\n\n"
        "<b>📱 Теперь укажите ваш номер телефона:</b>\n\n"
        "<i>Нажмите кнопку ниже, чтобы поделиться контактом, "
        "или нажмите 'Ввести вручную', чтобы написать номер самостоятельно.</i>",
        parse_mode="HTML",
        reply_markup=get_contact_keyboard()
    )


@user_router.message(BookingStates.waiting_for_contact, F.text == "✏️ Ввести вручную")
async def ask_for_manual_phone(message: Message):
    """Запрос ручного ввода телефона"""
    await message.answer(
        "📱 <b>Введите ваш номер телефона:</b>\n\n"
        "<i>Формат: +7 999 123-45-67 или 89991234567</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )


@user_router.message(BookingStates.waiting_for_contact, F.contact)
async def process_contact_auto(message: Message, state: FSMContext):
    """Обработка автоматического получения контакта"""
    phone = message.contact.phone_number
    await process_phone_number(message, state, phone)


@user_router.message(BookingStates.waiting_for_contact, F.text)
async def process_contact_manual(message: Message, state: FSMContext):
    """Обработка ручного ввода телефона"""
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return

    phone = message.text.strip()
    await process_phone_number(message, state, phone)


async def process_phone_number(message: Message, state: FSMContext, phone: str):
    """Общая обработка номера телефона"""
    # Очищаем номер от лишних символов
    cleaned_phone = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

    if not cleaned_phone.isdigit():
        await message.answer(
            "❌ <b>Неверный формат номера телефона.</b>\n\n"
            "Пожалуйста, введите номер еще раз или поделитесь контактом:",
            parse_mode="HTML",
            reply_markup=get_contact_keyboard()
        )
        return

    if len(cleaned_phone) < 10:
        await message.answer(
            "❌ <b>Номер телефона слишком короткий.</b>\n\n"
            "Пожалуйста, введите корректный номер:",
            parse_mode="HTML",
            reply_markup=get_contact_keyboard()
        )
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
        f"✅ <b>Контактные данные сохранены!</b>\n\n"
        f"📋 <b>Сводка вашего бронирования:</b>\n\n"
        f"{booking_summary}\n\n"
        f"<i>Проверьте все данные и подтвердите бронирование:</i>",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard()
    )


@user_router.callback_query(F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Подтверждение бронирования"""
    data = await state.get_data()

    # Сохраняем бронирование в БД
    session = get_session()
    try:
        booking = Booking(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=data['full_name'],
            phone=data['phone'],
            zone=data.get('zone', 'main'),
            table_number=data['table_number'],
            date=data['date'],
            time=data['time'],
            guests=data['guests'],
            status='pending'
        )
        session.add(booking)
        session.commit()

        booking_summary = format_booking_data(data)
        booking_id = booking.id

        # Уведомляем администраторов
        admin_notified = False
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"📥 <b>НОВАЯ ЗАЯВКА НА БРОНИРОВАНИЕ!</b>\n\n"
                    f"{booking_summary}\n\n"
                    f"🆔 ID брони: {booking_id}",
                    parse_mode="HTML",
                    reply_markup=get_booking_actions(booking_id)
                )
                admin_notified = True
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")

        # Форматируем дату для пользователя
        date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')

        await callback.message.edit_text(
            f"🎉 <b>БРОНИРОВАНИЕ ОФОРМЛЕНО!</b>\n\n"
            f"{booking_summary}\n\n"
            f"🆔 <b>Номер вашей заявки:</b> #{booking_id}\n\n"
            f"<i>Статус: <b>ожидает подтверждения</b></i>\n\n"
            f"📞 Мы свяжемся с вами для подтверждения.\n"
            f"⏰ Обычно это занимает не более 30 минут.\n\n"
            f"<i>Вы можете отслеживать статус брони в разделе '📋 Мои бронирования'.</i>",
            parse_mode="HTML"
        )

        if not admin_notified:
            await callback.message.answer(
                "⚠️ <b>Примечание:</b> В данный момент администратор недоступен. "
                "Мы уведомим его при первой возможности.",
                parse_mode="HTML"
            )

        await state.clear()

        # Предлагаем вернуться в меню
        await callback.message.answer(
            "Выберите дальнейшее действие:",
            reply_markup=get_main_menu()
        )

    except Exception as e:
        logger.error(f"Ошибка при сохранении бронирования: {e}")
        await callback.message.answer(
            "❌ <b>Произошла ошибка при сохранении бронирования.</b>\n\n"
            "Пожалуйста, попробуйте снова или свяжитесь с администратором.",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    finally:
        session.close()

    await callback.answer()


@user_router.callback_query(F.data == "cancel_booking")
async def cancel_booking_user(callback: CallbackQuery, state: FSMContext):
    """Отмена бронирования пользователем"""
    await state.clear()
    await callback.message.edit_text("❌ <b>Бронирование отменено.</b>", parse_mode="HTML")
    await callback.message.answer(
        "Вы можете начать новое бронирование в любое время:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ========== АДМИН КОМАНДЫ ==========

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Открытие админ-панели"""
    logger.info(f"Админ панель открыта пользователем {message.from_user.id}")

    session = get_session()
    try:
        # Статистика для админа
        total_bookings = session.query(Booking).count()
        pending_bookings = session.query(Booking).filter(Booking.status == 'pending').count()
        today_bookings = session.query(Booking).filter(
            Booking.date == datetime.now().strftime('%Y-%m-%d')
        ).count()

        await message.answer(
            f"👨‍💼 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
            f"👤 Ваш ID: <code>{message.from_user.id}</code>\n"
            f"📛 Имя: {message.from_user.full_name}\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего бронирований: {total_bookings}\n"
            f"• Ожидают подтверждения: {pending_bookings}\n"
            f"• Бронирований на сегодня: {today_bookings}\n\n"
            f"<i>Выберите действие:</i>",
            parse_mode="HTML",
            reply_markup=get_admin_menu()
        )

    finally:
        session.close()


@admin_router.message(F.text == "📊 Все бронирования")
async def show_all_bookings(message: Message):
    """Показать все бронирования"""
    session = get_session()
    try:
        bookings = session.query(Booking).order_by(
            Booking.date, Booking.time
        ).all()

        if not bookings:
            await message.answer("📭 <b>Нет активных бронирований.</b>", parse_mode="HTML")
            return

        await message.answer(
            f"📊 <b>Все бронирования ({len(bookings)}):</b>",
            parse_mode="HTML"
        )

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
    """Показать бронирования, ожидающие подтверждения"""
    session = get_session()
    try:
        bookings = session.query(Booking).filter(
            Booking.status == 'pending'
        ).order_by(Booking.created_at).all()

        if not bookings:
            await message.answer("✅ <b>Нет бронирований, ожидающих подтверждения.</b>", parse_mode="HTML")
            return

        await message.answer(
            f"⏳ <b>Ожидают подтверждения ({len(bookings)}):</b>",
            parse_mode="HTML"
        )

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML",
                reply_markup=get_booking_actions(booking.id)
            )

    finally:
        session.close()


@admin_router.message(F.text == "✅ Подтвержденные")
async def show_confirmed_bookings(message: Message):
    """Показать подтвержденные бронирования"""
    session = get_session()
    try:
        bookings = session.query(Booking).filter(
            Booking.status == 'confirmed'
        ).order_by(Booking.date, Booking.time).all()

        if not bookings:
            await message.answer("📭 <b>Нет подтвержденных бронирований.</b>", parse_mode="HTML")
            return

        await message.answer(
            f"✅ <b>Подтвержденные бронирования ({len(bookings)}):</b>",
            parse_mode="HTML"
        )

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML",
                reply_markup=get_booking_actions(booking.id)
            )

    finally:
        session.close()


@admin_router.message(F.text == "📅 На сегодня")
async def show_today_bookings(message: Message):
    """Показать бронирования на сегодня"""
    today = datetime.now().strftime('%Y-%m-%d')
    session = get_session()
    try:
        bookings = session.query(Booking).filter(
            Booking.date == today,
            Booking.status.in_(['pending', 'confirmed'])
        ).order_by(Booking.time).all()

        if not bookings:
            await message.answer(f"📅 <b>На сегодня ({datetime.now().strftime('%d.%m.%Y')}) нет бронирований.</b>",
                                 parse_mode="HTML")
            return

        await message.answer(
            f"📅 <b>Бронирования на сегодня ({len(bookings)}):</b>",
            parse_mode="HTML"
        )

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML",
                reply_markup=get_booking_actions(booking.id)
            )

    finally:
        session.close()


@admin_router.message(F.text == "📅 На завтра")
async def show_tomorrow_bookings(message: Message):
    """Показать бронирования на завтра"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    session = get_session()
    try:
        bookings = session.query(Booking).filter(
            Booking.date == tomorrow,
            Booking.status.in_(['pending', 'confirmed'])
        ).order_by(Booking.time).all()

        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')

        if not bookings:
            await message.answer(f"📅 <b>На завтра ({tomorrow_date}) нет бронирований.</b>", parse_mode="HTML")
            return

        await message.answer(
            f"📅 <b>Бронирования на завтра ({len(bookings)}):</b>",
            parse_mode="HTML"
        )

        for booking in bookings:
            await message.answer(
                format_booking(booking),
                parse_mode="HTML",
                reply_markup=get_booking_actions(booking.id)
            )

    finally:
        session.close()


@admin_router.message(F.text == "↩️ Назад в меню")
async def back_to_menu_admin(message: Message):
    """Возврат в главное меню для админа"""
    await message.answer(
        "🏠 <b>Возвращаюсь в главное меню...</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )


# ========== АДМИН КОЛЛБЭКИ ==========

@admin_router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_booking(callback: CallbackQuery):
    """Подтверждение бронирования админом"""
    booking_id = int(callback.data.split("_")[-1])

    session = get_session()
    try:
        booking = session.query(Booking).get(booking_id)
        if not booking:
            await callback.answer("❌ Бронь не найдена", show_alert=True)
            return

        booking.status = 'confirmed'
        session.commit()

        # Уведомляем пользователя
        try:
            await bot.send_message(
                booking.user_id,
                f"✅ <b>ВАША БРОНЬ ПОДТВЕРЖДЕНА!</b>\n\n"
                f"{format_booking_data(booking)}\n\n"
                f"📅 Мы ждем вас {booking.date} в {booking.time}\n"
                f"🪑 Столик №{booking.table_number}\n\n",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")

        await callback.message.edit_text(
            format_booking(booking),
            parse_mode="HTML",
            reply_markup=get_booking_actions(booking.id)
        )
        await callback.answer("✅ Бронь подтверждена!")

    finally:
        session.close()


@admin_router.message(F.text == "🗑️ Удалить неактуальные")
async def delete_outdated_bookings(message: Message):
    """Удаление прошедших (неактуальных) бронирований"""
    session = get_session()
    try:
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')

        # Находим прошедшие бронирования (дата < сегодня или дата = сегодня и время < текущего)
        outdated_bookings = session.query(Booking).filter(
            (Booking.date < today) |
            ((Booking.date == today) & (Booking.time < current_time))
        ).all()

        outdated_count = len(outdated_bookings)

        if outdated_count == 0:
            await message.answer(
                "✅ <b>Нет неактуальных (прошедших) бронирований.</b>\n"
                "Все бронирования актуальны.",
                parse_mode="HTML"
            )
            return

        # Удаляем
        for booking in outdated_bookings:
            session.delete(booking)

        session.commit()

        await message.answer(
            f"✅ <b>Удалено {outdated_count} неактуальных бронирований.</b>\n\n"
            f"🗑️ <b>Удалены:</b>\n"
            f"• Бронирования с прошедшей датой\n"
            f"• Бронирования с прошедшим временем сегодня\n\n"
            f"<i>Статусы бронирований: pending, confirmed, cancelled</i>",
            parse_mode="HTML"
        )

        logger.info(f"Админ {message.from_user.id} удалил {outdated_count} неактуальных бронирований")

    except Exception as e:
        logger.error(f"Ошибка при удалении неактуальных бронирований: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка при удалении.</b>\n"
            "Попробуйте позже или свяжитесь с разработчиком.",
            parse_mode="HTML"
        )
    finally:
        session.close()


@admin_router.message(F.text == "🗑️ Удалить отмененные")
async def delete_cancelled_bookings(message: Message):
    """Удаление всех отмененных бронирований"""
    session = get_session()
    try:
        # Находим все отмененные бронирования
        cancelled_bookings = session.query(Booking).filter(
            Booking.status == 'cancelled'
        ).all()

        cancelled_count = len(cancelled_bookings)

        if cancelled_count == 0:
            await message.answer(
                "✅ <b>Нет отмененных бронирований.</b>",
                parse_mode="HTML"
            )
            return

        # Удаляем
        for booking in cancelled_bookings:
            session.delete(booking)

        session.commit()

        await message.answer(
            f"✅ <b>Удалено {cancelled_count} отмененных бронирований.</b>\n\n"
            f"🗑️ <b>Удалены только бронирования со статусом 'cancelled'.</b>\n\n"
            f"<i>Активные брони (pending, confirmed) не затронуты.</i>",
            parse_mode="HTML"
        )

        logger.info(f"Админ {message.from_user.id} удалил {cancelled_count} отмененных бронирований")

    except Exception as e:
        logger.error(f"Ошибка при удалении отмененных бронирований: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка при удалении.</b>\n"
            "Попробуйте позже или свяжитесь с разработчиком.",
            parse_mode="HTML"
        )
    finally:
        session.close()



@admin_router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel_booking(callback: CallbackQuery):
    """Отмена бронирования админом"""
    booking_id = int(callback.data.split("_")[-1])

    session = get_session()
    try:
        booking = session.query(Booking).get(booking_id)
        if not booking:
            await callback.answer("❌ Бронь не найдена", show_alert=True)
            return

        booking.status = 'cancelled'
        session.commit()

        # Уведомляем пользователя
        try:
            await bot.send_message(
                booking.user_id,
                f"❌ <b>ВАША БРОНЬ ОТМЕНЕНА АДМИНИСТРАТОРОМ</b>\n\n"
                f"{format_booking_data(booking)}\n\n"
                f"<i>По вопросам обращайтесь к администратору по телефону:\n"
                f"{config.RESTAURANT_PHONE}</i>",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")

        await callback.message.edit_text(
            format_booking(booking),
            parse_mode="HTML",
            reply_markup=get_booking_actions(booking.id)
        )
        await callback.answer("❌ Бронь отменена")

    finally:
        session.close()


@admin_router.callback_query(F.data.startswith("admin_call_"))
async def admin_call_booking(callback: CallbackQuery):
    """Позвонить по бронированию"""
    booking_id = int(callback.data.split("_")[-1])

    session = get_session()
    try:
        booking = session.query(Booking).get(booking_id)
        if not booking:
            await callback.answer("❌ Бронь не найдена", show_alert=True)
            return

        await callback.answer(
            f"📞 Номер телефона: {booking.phone}\n"
            f"👤 Имя: {booking.full_name}",
            show_alert=True
        )

    finally:
        session.close()


@admin_router.callback_query(F.data.startswith("admin_details_"))
async def admin_details_booking(callback: CallbackQuery):
    """Детальная информация о бронировании"""
    booking_id = int(callback.data.split("_")[-1])

    session = get_session()
    try:
        booking = session.query(Booking).get(booking_id)
        if not booking:
            await callback.answer("❌ Бронь не найдена", show_alert=True)
            return

        # Получаем информацию о пользователе
        user = session.query(User).filter(User.user_id == booking.user_id).first()

        user_info = ""
        if user:
            user_info = (
                f"👤 Пользователь:\n"
                f"• ID: {user.user_id}\n"
                f"• Username: @{user.username or 'не указан'}\n"
                f"• Телефон в профиле: {user.phone or 'не указан'}\n"
                f"• Зарегистрирован: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

        details = (
            f"📋 <b>Детальная информация о брони #{booking.id}</b>\n\n"
            f"{format_booking_data(booking)}\n\n"
            f"{user_info}"
        )

        await callback.message.answer(details, parse_mode="HTML")
        await callback.answer()

    finally:
        session.close()


# ========== ОБРАБОТЧИК ДЛЯ НЕРАСПОЗНАННЫХ СООБЩЕНИЙ ==========

@user_router.message()
async def handle_other_messages(message: Message, state: FSMContext):
    """Обработчик для всех остальных сообщений"""
    current_state = await state.get_state()

    if current_state:
        state_name = current_state.split(":")[-1]

        # Понятные подсказки для каждого состояния
        state_hints = {
            "waiting_for_date": "📅 Пожалуйста, выберите дату из предложенных вариантов",
            "waiting_for_time": "⏰ Выберите время из предложенных вариантов",
            "waiting_for_table": "🪑 Выберите столик из предложенных вариантов",
            "waiting_for_guests": "👥 Выберите количество гостей",
            "waiting_for_name": "👤 Введите ваше имя для бронирования",
            "waiting_for_contact": "📱 Пожалуйста, поделитесь номером телефона или введите его вручную",
            "waiting_for_confirm": "📋 Подтвердите или отмените бронирование"
        }

        if state_name in state_hints:
            await message.answer(state_hints[state_name])
        else:
            await message.answer(
                "🤔 Кажется, вы сбились с пути. Используйте кнопки меню для навигации.",
                reply_markup=get_main_menu()
            )
    else:
        # Если не в состоянии, показываем главное меню с подсказкой
        await message.answer(
            "🎯 <b>Что вы хотите сделать?</b>\n\n"
            "Используйте кнопки меню для навигации:",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )


# ========== ФУНКЦИЯ АВТОМАТИЧЕСКОГО УДАЛЕНИЯ УСТАРЕВШИХ БРОНЕЙ ==========

async def cleanup_expired_bookings():
    """Автоматическое удаление устаревших бронирований"""
    while True:
        try:
            session = get_session()
            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M')

            # Удаляем прошедшие бронирования
            expired_bookings = session.query(Booking).filter(
                (Booking.date < today) |
                ((Booking.date == today) & (Booking.time < current_time))
            ).all()

            if expired_bookings:
                for booking in expired_bookings:
                    session.delete(booking)
                session.commit()
                logger.info(f"Удалено {len(expired_bookings)} устаревших бронирований")

            session.close()
        except Exception as e:
            logger.error(f"Ошибка при очистке устаревших бронирований: {e}")

        # Проверяем каждую минуту
        await asyncio.sleep(60)


# ========== ЗАПУСК БОТА ==========

async def main():
    """Основная функция запуска бота"""
    # Создаем директорию для данных, если её нет
    import os
    if not os.path.exists('data'):
        os.makedirs('data')
        logger.info("Создана директория 'data'")

    # Запускаем задачу по очистке устаревших бронирований
    asyncio.create_task(cleanup_expired_bookings())

    logger.info(f"Запуск бота для ресторана '{config.RESTAURANT_NAME}'")
    logger.info(f"Часы работы: {config.WORKING_HOURS_STR}")
    logger.info(f"Последняя бронь: {config.LAST_BOOKING_TIME_STR}")
    logger.info(f"Количество столиков: {len(config.TABLES['main'])}")
    logger.info(f"Администраторов: {len(config.ADMIN_IDS)}")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())