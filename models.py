"""
models.py
Модели: абстрактный Person, Guest, Room, Booking
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class Person(ABC):
    """Абстрактный класс человека — демонстрация ООП (абстракция + наследование)."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Уникальный идентификатор личности."""
        raise NotImplementedError

    @abstractmethod
    def contact_info(self) -> str:
        """Строковое представление контактной информации."""
        raise NotImplementedError


@dataclass
class Guest(Person):
    """Модель гостя, наследует абстрактный Person."""
    guest_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    @property
    def id(self) -> str:
        return self.guest_id

    def contact_info(self) -> str:
        parts = []
        if self.email:
            parts.append(f"email: {self.email}")
        if self.phone:
            parts.append(f"phone: {self.phone}")
        return ", ".join(parts) if parts else "no contacts"

    def __str__(self) -> str:
        return f"Guest {self.guest_id}: {self.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация гостя в JSON-совместимый словарь."""
        return {
            "guest_id": self.guest_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Guest":
        return Guest(
            guest_id=data["guest_id"],
            name=data["name"],
            email=data.get("email"),
            phone=data.get("phone")
        )


@dataclass
class Room:
    """Модель комнаты"""
    room_number: str
    room_type: str
    price_per_night: float
    is_occupied: bool = False

    def __str__(self) -> str:
        return f"Room {self.room_number} ({self.room_type}) - {'occupied' if self.is_occupied else 'free'}"

    def get_status(self) -> bool:
        """Возвращает True если занята."""
        return bool(self.is_occupied)

    def set_occupied(self, status: bool):
        """Установить статус занятости комнаты."""
        self.is_occupied = bool(status)

    def get_price(self) -> float:
        return float(self.price_per_night)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_number": self.room_number,
            "room_type": self.room_type,
            "price_per_night": self.price_per_night,
            "is_occupied": int(self.is_occupied)
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Room":
        return Room(
            room_number=str(data["room_number"]),
            room_type=data["room_type"],
            price_per_night=float(data["price_per_night"]),
            is_occupied=bool(int(data.get("is_occupied", 0)))
        )


@dataclass
class Booking:
    """Модель брони"""
    booking_id: str
    guest_id: str
    room_number: str
    check_in_date: date
    check_out_date: date
    status: str = field(default="booked")  # booked, checked_in, checked_out, cancelled
    total_price: Optional[float] = None

    def is_active(self) -> bool:
        """Вернёт True если бронь в статусе checked_in"""
        return self.status == "checked_in"

    def get_duration(self) -> int:
        """Возвращает количество ночей."""
        return (self.check_out_date - self.check_in_date).days

    def validate_dates(self):
        """Проверка корректности дат: выезд после заезда."""
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")

    def calculate_total(self, price_per_night: float) -> float:
        """Рассчитывает total_price по цене комнаты."""
        nights = self.get_duration()
        self.total_price = nights * price_per_night
        return self.total_price

    def update_status(self, new_status: str):
        self.status = new_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "booking_id": self.booking_id,
            "guest_id": self.guest_id,
            "room_number": self.room_number,
            "check_in_date": self.check_in_date.isoformat(),
            "check_out_date": self.check_out_date.isoformat(),
            "status": self.status,
            "total_price": self.total_price
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Booking":
        return Booking(
            booking_id=data["booking_id"],
            guest_id=data["guest_id"],
            room_number=data["room_number"],
            check_in_date=date.fromisoformat(data["check_in_date"]),
            check_out_date=date.fromisoformat(data["check_out_date"]),
            status=data.get("status", "booked"),
            total_price=data.get("total_price")
        )
