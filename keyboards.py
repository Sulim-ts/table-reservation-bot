from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from config import config
from utils import get_available_tables


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


# Клавиатура для быстрого выбора даты
def get_date_selection():
    today = datetime.now()

    # Кнопки на ближайшие дни
    keyboard = []

    # Сегодня
    today_str = today.strftime('%Y-%m-%d')
    keyboard.append([
        InlineKeyboardButton(text=f"📅 Сегодня ({today.day}.{today.month})", callback_data=f"date_{today_str}")
    ])

    # Завтра
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    keyboard.append([
        InlineKeyboardButton(text=f"📅 Завтра ({tomorrow.day}.{tomorrow.month})", callback_data=f"date_{tomorrow_str}")
    ])

    # Послезавтра
    day_after = today + timedelta(days=2)
    day_after_str = day_after.strftime('%Y-%m-%d')
    keyboard.append([
        InlineKeyboardButton(text=f"📅 Послезавтра ({day_after.day}.{day_after.month})",
                             callback_data=f"date_{day_after_str}")
    ])

    # Календарь для выбора любой даты
    keyboard.append([
        InlineKeyboardButton(text="🗓️ Выбрать другую дату", callback_data="select_month")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для выбора времени с эмодзи статуса
def get_time_slots(date, zone='main'):
    keyboard = []

    # Заголовок с датой
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')

    # Разделяем утро, день и вечер
    morning_slots = []
    afternoon_slots = []
    evening_slots = []

    for hour in range(config.OPEN_TIME, config.CLOSE_TIME):
        for minute in ['00', '30']:
            time_str = f"{hour:02d}:{minute}"
            available_tables = get_available_tables(date, time_str, zone)

            # Определяем период дня
            if hour < 15:
                period_list = morning_slots
                period_emoji = "🌅"
            elif hour < 19:
                period_list = afternoon_slots
                period_emoji = "🌇"
            else:
                period_list = evening_slots
                period_emoji = "🌃"

            if available_tables:
                free_count = len(available_tables)
                button_text = f"{period_emoji} {time_str} (свободно: {free_count})"
                period_list.append(InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"time_{time_str}"
                ))
            else:
                button_text = f"❌ {time_str} (нет мест)"
                period_list.append(InlineKeyboardButton(
                    text=button_text,
                    callback_data="no_tables"
                ))

    # Добавляем слоты по периодам с заголовками
    if morning_slots:
        keyboard.append([InlineKeyboardButton(text="🌅 Утро (12:00 - 15:00)", callback_data="no_tables")])
        keyboard += [morning_slots[i:i + 2] for i in range(0, len(morning_slots), 2)]

    if afternoon_slots:
        keyboard.append([InlineKeyboardButton(text="🌇 День (15:00 - 19:00)", callback_data="no_tables")])
        keyboard += [afternoon_slots[i:i + 2] for i in range(0, len(afternoon_slots), 2)]

    if evening_slots:
        keyboard.append([InlineKeyboardButton(text="🌃 Вечер (19:00 - 23:00)", callback_data="no_tables")])
        keyboard += [evening_slots[i:i + 2] for i in range(0, len(evening_slots), 2)]

    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(text="↩️ Выбрать другую дату", callback_data="back_to_date_selection")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура выбора столиков с визуальной схемой
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

    # Легенда
    keyboard.append([
        InlineKeyboardButton(text="🟢 - свободно", callback_data="no_tables"),
        InlineKeyboardButton(text="🔴 - занято", callback_data="no_tables")
    ])

    # Кнопки навигации
    keyboard.append([
        InlineKeyboardButton(text="↩️ Выбрать другое время", callback_data="back_to_time_selection"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="cancel_booking")
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
        InlineKeyboardButton(text="↩️ Отменить бронирование", callback_data="cancel_booking"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="go_to_menu")
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
            InlineKeyboardButton(text="✅ Да, забронировать!", callback_data="confirm_booking"),
            InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_booking")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="go_to_menu")
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
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_delete_{booking_id}")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить время", callback_data=f"admin_edit_time_{booking_id}"),
            InlineKeyboardButton(text="ℹ️ Детали", callback_data=f"admin_details_{booking_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для фильтрации бронирований (админ)
def get_admin_filter_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="📅 Сегодня", callback_data="admin_today"),
            InlineKeyboardButton(text="📅 Завтра", callback_data="admin_tomorrow")
        ],
        [
            InlineKeyboardButton(text="⏳ Ожидают", callback_data="admin_pending"),
            InlineKeyboardButton(text="✅ Подтвержденные", callback_data="admin_confirmed")
        ],
        [
            InlineKeyboardButton(text="❌ Отмененные", callback_data="admin_cancelled"),
            InlineKeyboardButton(text="📊 Все", callback_data="admin_all")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Класс для работы с календарем
class DateKeyboard:
    @staticmethod
    def get_months_keyboard():
        today = datetime.now()

        keyboard = []

        # Русские названия месяцев
        month_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }

        # Показываем текущий и 2 следующих месяца
        for i in range(3):
            month_date = today + timedelta(days=30 * i)
            month_key = f"{month_date.year}-{month_date.month}"
            month_name = month_names.get(month_date.month, f"Месяц {month_date.month}")
            year_display = f" {month_date.year}" if today.year != month_date.year else ""

            keyboard.append([
                InlineKeyboardButton(
                    text=f"📅 {month_name}{year_display}",
                    callback_data=f"month_{month_key}"
                )
            ])

        # Кнопка назад
        keyboard.append([
            InlineKeyboardButton(text="↩️ Назад к выбору даты", callback_data="back_to_date_selection")
        ])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_days_for_month(month_key):
        try:
            year, month = map(int, month_key.split('-'))

            today = datetime.now()
            selected_date = datetime(year, month, 1)
            max_date = today + timedelta(days=30)

            if selected_date > max_date:
                return None

            # Получаем количество дней в месяце
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)

            days_in_month = (next_month - selected_date).days

            keyboard = []

            # Заголовок с названием месяца
            month_names = {
                1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
                5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
                9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
            }
            month_name = month_names.get(month, f"Месяц {month}")

            keyboard.append([
                InlineKeyboardButton(
                    text=f"📅 {month_name} {year}",
                    callback_data="no_tables"
                )
            ])

            row = []

            for day in range(1, days_in_month + 1):
                date_str = f"{year}-{month:02d}-{day:02d}"
                current_date = datetime(year, month, day).date()

                # Пропускаем прошедшие даты
                if current_date < today.date() or current_date > max_date.date():
                    continue

                # Определяем эмодзи для даты
                if current_date == today.date():
                    emoji = "🟢"
                elif current_date == today.date() + timedelta(days=1):
                    emoji = "🟡"
                else:
                    emoji = "⚪"

                row.append(InlineKeyboardButton(
                    text=f"{emoji} {day}",
                    callback_data=f"date_{date_str}"
                ))

                if len(row) == 7:
                    keyboard.append(row)
                    row = []

            if row:
                keyboard.append(row)

            # Кнопка назад
            keyboard.append([
                InlineKeyboardButton(text="↩️ Выбрать другой месяц", callback_data="select_month")
            ])

            if len(keyboard) > 2:  # Если есть хотя бы одна дата
                return InlineKeyboardMarkup(inline_keyboard=keyboard)
            else:
                return None

        except ValueError:
            return None