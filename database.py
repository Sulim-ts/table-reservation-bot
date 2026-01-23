from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pytz

Base = declarative_base()


class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    username = Column(String)
    full_name = Column(String)
    phone = Column(String)
    zone = Column(String, default='main')  # теперь только 'main'
    table_number = Column(Integer)
    date = Column(String)  # YYYY-MM-DD
    time = Column(String)  # HH:MM
    guests = Column(Integer)
    status = Column(String, default='pending')  # pending, confirmed, cancelled
    created_at = Column(DateTime, default=datetime.now(pytz.timezone('Europe/Moscow')))
    admin_notified = Column(Boolean, default=False)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    full_name = Column(String)
    phone = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(pytz.timezone('Europe/Moscow')))


# Создаем базу данных
engine = create_engine('sqlite:///data/database.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


def get_session():
    return Session()