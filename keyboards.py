from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from config import config
from utils import get_available_tables, is_within_working_hours, generate_time_slots


# Основное меню (более интуитивное)
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Забронировать столик")],
            [KeyboardButton(text="📋 Мои бронирования"), KeyboardButton(text="ℹ️ О нас")],
            [KeyboardButton(text="🆘 Помощь"), KeyboardButton(text="📞 Контакты")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие 👆"
    )
    return keyboard


# Меню администратора
def get_admin_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Все бронирования")],
            [KeyboardButton(text="⏳ Ожидают подтверждения"), KeyboardButton(text="✅ Подтвержденные")],
            [KeyboardButton(text="📅 На сегодня"), KeyboardButton(text="📅 На завтра")],
            [KeyboardButton(text="↩️ Назад в меню")]
        ],
        resize_keyboard=True
    )
    return keyboard


# Клавиатура для выбора даты (просто числа на 10 дней вперед)
def get_date_selection():
    today = datetime.now()

    keyboard = []
    row = []

    # Показываем 10 дней вперед, включая сегодня
    for i in range(10):
        day_date = today + timedelta(days=i)
        date_str = day_date.strftime('%Y-%m-%d')

        # Форматируем отображение: просто число месяца
        day_num = day_date.day

        # Проверяем, есть ли доступное время на этот день
        # Если сегодняшний день и уже позже времени последней брони - не показываем
        if i == 0:
            now = datetime.now()
            now_in_minutes = now.hour * 60 + now.minute
            if now_in_minutes > config.LAST_BOOKING_TIME_MINUTES:
                continue  # Пропускаем сегодняшний день

        # Эмодзи для сегодня и завтра
        if i == 0:
            day_text = f"🟢 {day_num}"
        elif i == 1:
            day_text = f"🟡 {day_num}"
        else:
            day_text = f"⚪ {day_num}"

        row.append(InlineKeyboardButton(
            text=day_text,
            callback_data=f"date_{date_str}"
        ))

        if len(row) == 5:  # 5 кнопок в ряду
            keyboard.append(row)
            row = []

    # Добавляем оставшиеся кнопки
    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для выбора времени с учетом интервала
def get_time_slots(date, zone='main'):
    keyboard = []

    # Заголовок с датой
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')

    # Проверяем, сегодняшний ли день
    today = datetime.now().date()
    selected_date = date_obj.date()

    row = []
    time_slots = generate_time_slots()

    for time_str in time_slots:
        # Для сегодняшнего дня проверяем, что время в будущем
        if selected_date == today:
            now = datetime.now()
            slot_hour, slot_minute = map(int, time_str.split(':'))
            now_in_minutes = now.hour * 60 + now.minute
            slot_in_minutes = slot_hour * 60 + slot_minute

            if now_in_minutes >= slot_in_minutes:
                continue  # Пропускаем прошедшее время

        if is_within_working_hours(time_str):
            available_tables = get_available_tables(date, time_str, zone)

            if available_tables:
                free_count = len(available_tables)
                button_text = f"{time_str} ({free_count} мест)"
                row.append(InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"time_{time_str}"
                ))
            else:
                button_text = f"{time_str} (нет мест)"
                row.append(InlineKeyboardButton(
                    text=button_text,
                    callback_data="no_tables"
                ))

        if len(row) == 2:  # 2 кнопки в ряду
            keyboard.append(row)
            row = []

    if row:  # Добавляем оставшиеся кнопки
        keyboard.append(row)

    # Если нет доступного времени
    if not keyboard:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Нет доступного времени на этот день",
                callback_data="no_tables"
            )
        ])

    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(text="↩️ Назад к выбору даты", callback_data="back_to_date_selection")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_menu():
    """Клавиатура администратора"""
    keyboard = [
        [KeyboardButton(text="📊 Все бронирования")],
        [KeyboardButton(text="⏳ Ожидают подтверждения")],
        [KeyboardButton(text="✅ Подтвержденные")],
        [KeyboardButton(text="📅 На сегодня")],
        [KeyboardButton(text="📅 На завтра")],
        [KeyboardButton(text="🗑️ Удалить неактуальные")],
        [KeyboardButton(text="🗑️ Удалить отмененные")],
        [KeyboardButton(text="↩️ Назад в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# Клавиатура выбора столиков
def get_tables_keyboard(date, time, zone='main'):
    available_tables = get_available_tables(date, time, zone)

    keyboard = []

    # Заголовок с информацией
    keyboard.append([
        InlineKeyboardButton(
            text=f"🕐 {time} | Выберите столик:",
            callback_data="no_tables"
        )
    ])

    # Если нет свободных столиков или время позже последней брони
    if not available_tables:
        # Проверяем, почему нет столиков
        hour, minute = map(int, time.split(':'))
        time_in_minutes = hour * 60 + minute

        if time_in_minutes > config.LAST_BOOKING_TIME_MINUTES:
            message = f"❌ Бронирование после {config.LAST_BOOKING_TIME_STR} невозможно"
        else:
            message = "❌ Нет свободных столиков на это время"

        keyboard.append([
            InlineKeyboardButton(
                text=message,
                callback_data="no_tables"
            )
        ])
    else:
        row = []

        for table_num in config.TABLES.get(zone, []):
            if table_num in available_tables:
                button_text = f"🟢 {table_num}"
                callback_data = f"table_{table_num}"
            else:
                button_text = f"🔴 {table_num}"
                callback_data = "no_tables"

            row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

            if len(row) == 4:  # 4 кнопки в ряду для лучшего отображения
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

    # Кнопки навигации
    keyboard.append([
        InlineKeyboardButton(text="↩️ Назад к выбору времени", callback_data="back_to_time_selection")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для выбора количества гостей
def get_guests_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="👤 1-2 гостя", callback_data="guests_2")],
        [InlineKeyboardButton(text="👥 3-4 гостя", callback_data="guests_4")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 5-6 гостей", callback_data="guests_6")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦👨‍👩‍👧‍👦 7+ гостей", callback_data="guests_more")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для выбора точного количества гостей (если выбрано 7+)
def get_more_guests_keyboard():
    keyboard = []
    row = []

    for guests in range(7, config.MAX_GUESTS + 1):
        row.append(InlineKeyboardButton(text=str(guests), callback_data=f"guests_{guests}"))

        if len(row) == 4:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_guests")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для ввода имени
def get_name_input_keyboard():
    keyboard = [[
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_guests")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для ввода контакта
def get_contact_keyboard():
    keyboard = [[
        KeyboardButton(text="📱 Отправить мой контакт", request_contact=True)
    ], [
        KeyboardButton(text="✏️ Ввести вручную")
    ]]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Поделитесь контактом или введите номер"
    )


# Клавиатура для подтверждения бронирования
def get_confirm_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить бронь", callback_data="confirm_booking"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для действий с бронированием (админ)
def get_booking_actions(booking_id):
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{booking_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_cancel_{booking_id}")
        ],
        [
            InlineKeyboardButton(text="📞 Позвонить", callback_data=f"admin_call_{booking_id}"),
            InlineKeyboardButton(text="ℹ️ Детали", callback_data=f"admin_details_{booking_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатуры "Назад" для каждого этапа
def get_back_to_dates_keyboard():
    keyboard = [[
        InlineKeyboardButton(text="↩️ Назад к выбору даты", callback_data="back_to_date_selection")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_times_keyboard():
    keyboard = [[
        InlineKeyboardButton(text="↩️ Назад к выбору времени", callback_data="back_to_time_selection")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)




def get_back_to_tables_keyboard():
    keyboard = [[
        InlineKeyboardButton(text="↩️ Назад к выбору столика", callback_data="back_to_time_selection")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_guests_keyboard():
    keyboard = [[
        InlineKeyboardButton(text="↩️ Назад к выбору гостей", callback_data="back_to_guests")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)