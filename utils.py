from datetime import datetime, timedelta
from database import get_session, Booking
from config import config


def format_booking(booking):
    zone_name = config.ZONES.get(booking.zone, booking.zone)
    status_translations = {
        'pending': 'на рассмотрении',
        'confirmed': 'подтверждено',
        'cancelled': 'отменено'
    }

    status_display = status_translations.get(booking.status, booking.status)

    return (
        f"{'📋' if booking.status == 'pending' else '✅' if booking.status == 'confirmed' else '❌'} <b>Бронь #{booking.id}</b>\n"
        f"📅 Дата: {booking.date}\n"
        f"⏰ Время: {booking.time}\n"
        f"🎯 Зона: {zone_name}\n"
        f"🪑 Столик: {booking.table_number}\n"
        f"👥 Гостей: {booking.guests}\n"
        f"📞 Телефон: {booking.phone}\n"
        f"👤 Имя: {booking.full_name}\n"
        f"📊 Статус: {status_display}\n"
        f"🕒 Создано: {booking.created_at.strftime('%d.%m.%Y %H:%M')}"
    )


def get_booked_tables(date, time, zone='main'):
    session = get_session()
    try:
        query = session.query(Booking).filter(
            Booking.date == date,
            Booking.time == time,
            Booking.status.in_(['pending', 'confirmed']),
            Booking.zone == zone
        )

        bookings = query.all()
        return [booking.table_number for booking in bookings]
    finally:
        session.close()


def get_available_tables(date, time, zone='main'):
    # Проверяем, не позже ли времени последней брони
    try:
        hour, minute = map(int, time.split(':'))
        time_in_minutes = hour * 60 + minute

        # Если время позже времени последней брони
        if time_in_minutes > config.LAST_BOOKING_TIME_MINUTES:
            return []
    except:
        pass

    booked_tables = get_booked_tables(date, time, zone)
    all_tables = config.TABLES.get(zone, [])
    return [table for table in all_tables if table not in booked_tables]


def validate_date(date_str):
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        max_date = today + timedelta(days=10)  # Бронирование максимум на 10 дней вперед

        if date < today:
            return False, "Нельзя бронировать на прошедшую дату"
        if date > max_date:
            return False, f"Бронирование возможно максимум на 10 дней вперед (до {max_date.strftime('%d.%m.%Y')})"
        return True, date_str
    except ValueError:
        return False, "Неверный формат даты"


def validate_time(time_str):
    try:
        hour, minute = map(int, time_str.split(':'))
        time_in_minutes = hour * 60 + minute

        # Проверяем, что время в будущем, если выбрана сегодняшняя дата
        today = datetime.now().date()

        if 'date' in locals() or 'date' in globals():
            # Если дата передана, проверяем для сегодняшнего дня
            if date == today.strftime('%Y-%m-%d'):
                now = datetime.now()
                selected_time = datetime.strptime(time_str, '%H:%M').time()
                if now.time() > selected_time:
                    return False, f"Нельзя бронировать на прошедшее время. Сейчас {now.strftime('%H:%M')}"

        # Проверяем рабочее время
        if time_in_minutes < config.OPEN_TIME_MINUTES:
            return False, f"Мы открываемся в {config.OPEN_TIME_STR}"

        if time_in_minutes >= config.CLOSE_TIME_MINUTES:
            return False, f"Мы закрываемся в {config.CLOSE_TIME_STR}"

        # Проверяем, что время последней брони не позднее чем за час до закрытия
        if time_in_minutes > config.LAST_BOOKING_TIME_MINUTES:
            return False, f"Последняя бронь возможна до {config.LAST_BOOKING_TIME_STR}"

        # Проверяем, что время соответствует интервалу
        if minute % (config.TIME_INTERVAL % 60) != 0:
            interval_str = f"{config.TIME_INTERVAL} минут"
            if config.TIME_INTERVAL == 60:
                interval_str = "целый час"
            return False, f"Бронирование возможно с интервалом {interval_str}"

        return True, time_str
    except ValueError:
        return False, "Неверный формат времени"


def format_booking_data(data):
    if isinstance(data, Booking):
        zone_name = config.ZONES.get(data.zone, data.zone)
        status_translations = {
            'pending': 'на рассмотрении',
            'confirmed': 'подтверждено',
            'cancelled': 'отменено'
        }
        status_display = status_translations.get(data.status, data.status)

        return (
            f"📅 Дата: {data.date}\n"
            f"⏰ Время: {data.time}\n"
            f"🎯 Зона: {zone_name}\n"
            f"🪑 Столик: {data.table_number}\n"
            f"👥 Гостей: {data.guests}\n"
            f"📞 Телефон: {data.phone}\n"
            f"👤 Имя: {data.full_name}\n"
            f"📊 Статус: {status_display}"
        )
    else:
        zone_name = config.ZONES.get(data.get('zone', 'main'), 'Основной зал')
        return (
            f"📅 Дата: {data['date']}\n"
            f"⏰ Время: {data['time']}\n"
            f"🎯 Зона: {zone_name}\n"
            f"🪑 Столик: {data['table_number']}\n"
            f"👥 Гостей: {data['guests']}\n"
            f"📞 Телефон: {data['phone']}\n"
            f"👤 Имя: {data['full_name']}\n"
            f"📊 Статус: на рассмотрении"
        )


def validate_time_for_today(date_str, time_str):
    """Проверка, что время в будущем для сегодняшней даты"""
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = datetime.now().date()

        if selected_date == today:
            now = datetime.now()
            selected_time = datetime.strptime(time_str, '%H:%M').time()
            if now.time() > selected_time:
                return False, f"Нельзя бронировать на прошедшее время. Сейчас {now.strftime('%H:%M')}"

        return True, "Время доступно"
    except Exception as e:
        return False, f"Ошибка при проверке времени: {e}"


def is_within_working_hours(time_str):
    """Проверяет, что время в рабочее время и не позже времени последней брони"""
    try:
        hour, minute = map(int, time_str.split(':'))
        time_in_minutes = hour * 60 + minute

        # Проверка рабочего времени
        if time_in_minutes < config.OPEN_TIME_MINUTES:
            return False

        if time_in_minutes >= config.CLOSE_TIME_MINUTES:
            return False

        # Проверка, что не позже времени последней брони
        if time_in_minutes > config.LAST_BOOKING_TIME_MINUTES:
            return False

        return True
    except:
        return False


def generate_time_slots():
    """Генерация временных слотов на основе интервала"""
    slots = []
    current_minutes = config.OPEN_TIME_MINUTES

    while current_minutes <= config.LAST_BOOKING_TIME_MINUTES:
        hour = current_minutes // 60
        minute = current_minutes % 60
        time_str = f"{hour:02d}:{minute:02d}"
        slots.append(time_str)
        current_minutes += config.TIME_INTERVAL

    return slots

