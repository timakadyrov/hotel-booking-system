"""
notification.py
Абстрактный NotificationService и реализации
"""

from abc import ABC, abstractmethod
from typing import Optional


class NotificationService(ABC):
    """Абстрактный сервис уведомлений (интерфейс)."""

    @abstractmethod
    def send_booking_confirmation(self, guest_email: Optional[str], booking_id: str):
        raise NotImplementedError

    @abstractmethod
    def send_payment_confirmation(self, guest_email: Optional[str], payment_info: dict):
        raise NotImplementedError

    @abstractmethod
    def send_checkin_reminder(self, guest_email: Optional[str], booking_id: str):
        raise NotImplementedError

    @abstractmethod
    def send_checkout_reminder(self, guest_email: Optional[str], booking_id: str):
        raise NotImplementedError

    @abstractmethod
    def send_booking_cancellation(self, guest_email: Optional[str], booking_id: str):
        raise NotImplementedError

    @abstractmethod
    def send_sms_notification(self, phone: Optional[str], message: str):
        raise NotImplementedError


class EmailNotification(NotificationService):
    """Простая реализация email уведомлений (печать в консоль)."""

    def __init__(self, smtp_server: str = "smtp.example.com", smtp_port: int = 25):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_booking_confirmation(self, guest_email: Optional[str], booking_id: str):
        if guest_email:
            print(f"[Email] to={guest_email} subject=Booking confirmation message=Ваша бронь {booking_id} подтверждена")
            return True
        return False

    def send_payment_confirmation(self, guest_email: Optional[str], payment_info: dict):
        if guest_email:
            print(f"[Email] to={guest_email} subject=Payment confirmation message=Оплата {payment_info.get('amount')} принята")
            return True
        return False

    def send_checkin_reminder(self, guest_email: Optional[str], booking_id: str):
        if guest_email:
            print(f"[Email] to={guest_email} subject=Check-in reminder message=Напоминание: заселение {booking_id}")
            return True
        return False

    def send_checkout_reminder(self, guest_email: Optional[str], booking_id: str):
        if guest_email:
            print(f"[Email] to={guest_email} subject=Check-out reminder message=Напоминание: выселение {booking_id}")
            return True
        return False

    def send_booking_cancellation(self, guest_email: Optional[str], booking_id: str):
        if guest_email:
            print(f"[Email] to={guest_email} subject=Booking cancelled message=Бронь {booking_id} отменена")
            return True
        return False

    def send_sms_notification(self, phone: Optional[str], message: str):
        if phone:
            print(f"[SMS] to={phone} message={message}")
            return True
        return False


class SMSNotification(NotificationService):
    """Простая реализация SMS (печать)."""

    def send_booking_confirmation(self, guest_email: Optional[str], booking_id: str):
        # SMS implementation doesn't use email - not applicable
        return False

    def send_payment_confirmation(self, guest_email: Optional[str], payment_info: dict):
        return False

    def send_checkin_reminder(self, guest_email: Optional[str], booking_id: str):
        return False

    def send_checkout_reminder(self, guest_email: Optional[str], booking_id: str):
        return False

    def send_booking_cancellation(self, guest_email: Optional[str], booking_id: str):
        return False

    def send_sms_notification(self, phone: Optional[str], message: str):
        if phone:
            print(f"[SMS] to={phone} message={message}")
            return True
        return False
