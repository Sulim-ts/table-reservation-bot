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


def get_booked_tables(date, time, zone='main'):  # по умолчанию 'main'
    session = get_session()
    try:
        query = session.query(Booking).filter(
            Booking.date == date,
            Booking.time == time,
            Booking.status.in_(['pending', 'confirmed']),
            Booking.zone == zone  # только основной зал
        )

        bookings = query.all()
        return [booking.table_number for booking in bookings]
    finally:
        session.close()


def get_available_tables(date, time, zone='main'):  # по умолчанию 'main'
    booked_tables = get_booked_tables(date, time, zone)
    all_tables = config.TABLES.get(zone, [])
    return [table for table in all_tables if table not in booked_tables]


def validate_date(date_str):
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        max_date = today + timedelta(days=30)

        if date < today:
            return False, "Нельзя бронировать на прошедшую дату"
        if date > max_date:
            return False, "Бронирование возможно максимум на 30 дней вперед"
        return True, date_str
    except ValueError:
        return False, "Неверный формат даты"


def validate_time(time_str):
    try:
        hour, minute = map(int, time_str.split(':'))
        if hour < config.OPEN_TIME or hour >= config.CLOSE_TIME:
            return False, f"Мы работаем с {config.OPEN_TIME}:00 до {config.CLOSE_TIME}:00"
        if minute not in [0, 30]:
            return False, "Бронирование возможно только на 00 или 30 минут"
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