from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import config
from datetime import datetime, timedelta


def get_main_menu():
    keyboard = [
        [KeyboardButton(text="📅 Забронировать столик")],
        [KeyboardButton(text="📋 Мои бронирования")],
        [KeyboardButton(text="📞 Контакты")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_date_selection():
    """Получить клавиатуру для выбора даты с кнопками Сегодня, Завтра и Выбор месяца"""
    builder = InlineKeyboardBuilder()

    # Текущая дата
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    # Форматируем для отображения
    today_display = today.strftime("%d.%m.%Y")
    tomorrow_display = tomorrow.strftime("%d.%m.%Y")

    # Добавляем кнопки "Сегодня" и "Завтра"
    builder.add(InlineKeyboardButton(
        text=f"📅 Сегодня ({today_display})",
        callback_data=f"date_{today.strftime('%Y-%m-%d')}"
    ))
    builder.add(InlineKeyboardButton(
        text=f"📅 Завтра ({tomorrow_display})",
        callback_data=f"date_{tomorrow.strftime('%Y-%m-%d')}"
    ))

    # Добавляем кнопку для выбора другого дня
    builder.add(InlineKeyboardButton(
        text="📆 Выбрать другую дату",
        callback_data="select_month"
    ))

    builder.adjust(1)  # Все кнопки в один столбец
    return builder.as_markup()


def get_zones_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🎵 Караоке зал",
        callback_data="zone_karaoke"
    ))
    builder.add(InlineKeyboardButton(
        text="🤫 Тихий зал",
        callback_data="zone_quiet"
    ))
    return builder.as_markup()


def get_tables_keyboard(date, time, zone):
    """Показываем только свободные столики"""
    from utils import get_available_tables

    builder = InlineKeyboardBuilder()
    available_tables = get_available_tables(date, time, zone)

    if not available_tables:
        # Если нет свободных столиков
        builder.add(InlineKeyboardButton(
            text="❌ Нет свободных столиков",
            callback_data="no_tables"
        ))
    else:
        for table in available_tables:
            builder.add(InlineKeyboardButton(
                text=f"🪑 Столик {table}",
                callback_data=f"table_{table}"
            ))

    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


def get_time_slots(date, zone):
    """Генерация клавиатуры с временными слотами"""
    from utils import validate_date

    builder = InlineKeyboardBuilder()

    # Проверяем, что дата валидна
    valid, _ = validate_date(date)

    if not valid:
        return builder.as_markup()

    # Генерируем слоты времени
    for hour in range(config.OPEN_TIME, config.CLOSE_TIME):
        for minute in ['00', '30']:
            time_str = f"{hour:02d}:{minute}"

            # Проверяем, не прошло ли это время
            try:
                slot_datetime = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
                if slot_datetime < datetime.now():
                    continue  # Пропускаем прошедшее время
            except ValueError:
                pass

            builder.add(InlineKeyboardButton(
                text=time_str,
                callback_data=f"time_{time_str}"
            ))

    builder.adjust(4)
    return builder.as_markup()


def get_guests_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(1, 7):
        builder.add(InlineKeyboardButton(
            text=str(i),
            callback_data=f"guests_{i}"
        ))
    builder.adjust(3)
    return builder.as_markup()


def get_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить",
        callback_data="confirm_booking"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="cancel_booking"
    ))
    return builder.as_markup()


def get_contact_keyboard():
    keyboard = [[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_name_input_keyboard():
    """Клавиатура для ввода имени (без кнопок, только текстовый ввод)"""
    return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)


def get_admin_menu():
    keyboard = [
        [KeyboardButton(text="📊 Все бронирования")],
        [KeyboardButton(text="⏳ Ожидают подтверждения")],
        [KeyboardButton(text="📅 Бронирования на сегодня")],
        [KeyboardButton(text="↩️ Назад в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_booking_actions(booking_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить",
        callback_data=f"admin_confirm_{booking_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data=f"admin_cancel_{booking_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="✏️ Изменить время",
        callback_data=f"admin_edit_time_{booking_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑️ Удалить",
        callback_data=f"admin_delete_{booking_id}"
    ))
    builder.adjust(2)
    return builder.as_markup()


class DateKeyboard:
    """Класс для работы с клавиатурой выбора даты"""

    @staticmethod
    def get_dates_for_period():
        """Получить список дат на 30 дней вперед с разбивкой по месяцам"""
        today = datetime.now().date()
        dates_by_month = {}

        for i in range(30):  # 30 дней вперед
            current_date = today + timedelta(days=i)
            month_key = current_date.strftime("%Y-%m")
            month_name = current_date.strftime("%B %Y").lower()

            if month_key not in dates_by_month:
                # Русские названия месяцев
                month_translation = {
                    "january": "январь", "february": "февраль", "march": "март",
                    "april": "апрель", "may": "май", "june": "июнь",
                    "july": "июль", "august": "август", "september": "сентябрь",
                    "october": "октябрь", "november": "ноябрь", "december": "декабрь"
                }

                # Перевод названия месяца
                english_month = current_date.strftime("%B").lower()
                russian_month = month_translation.get(english_month, english_month)

                dates_by_month[month_key] = {
                    'name': russian_month,
                    'year': current_date.year,
                    'dates': []
                }

            dates_by_month[month_key]['dates'].append({
                'date': current_date,
                'display': str(current_date.day),  # Просто число
                'callback': current_date.strftime("%Y-%m-%d")
            })

        return dates_by_month

    @staticmethod
    def get_months_keyboard():
        """Получить клавиатуру с выбором месяца"""
        dates_by_month = DateKeyboard.get_dates_for_period()
        builder = InlineKeyboardBuilder()

        for month_data in dates_by_month.values():
            month_name = month_data['name'].capitalize()
            year = month_data['year']

            builder.add(InlineKeyboardButton(
                text=f"{month_name} {year}",
                callback_data=f"month_{month_data['dates'][0]['date'].strftime('%Y-%m')}"
            ))

        # Добавляем кнопку "Назад"
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_date_selection"
        ))

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_days_for_month(month_key):
        """Получить клавиатуру с днями месяца"""
        dates_by_month = DateKeyboard.get_dates_for_period()

        if month_key not in dates_by_month:
            return None

        builder = InlineKeyboardBuilder()
        month_data = dates_by_month[month_key]

        # Добавляем дни месяца
        for day_data in month_data['dates']:
            builder.add(InlineKeyboardButton(
                text=day_data['display'],  # Просто число
                callback_data=f"date_{day_data['callback']}"
            ))

        # Добавляем кнопку "Назад к выбору месяца"
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="select_month"
        ))

        # Автоматически подбираем количество кнопок в ряд
        # Первые строки - по 7 кнопок (дни недели), последняя - кнопка "Назад"
        total_days = len(month_data['dates'])
        rows = (total_days + 6) // 7  # Вычисляем количество полных строк

        # Сначала настраиваем дни (по 7 в ряд)
        builder.adjust(7, *[7] * (rows - 1), 1)  # Последний ряд для кнопки "Назад"

        return builder.as_markup()