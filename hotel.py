"""
hotel.py
Логика управления отелем
"""

from datetime import date
from typing import List, Optional, Dict, Any
import uuid
import json
from pathlib import Path

import db
import sqlite3
from models import Room, Guest, Booking
from payment import Payment
from notification import NotificationService

JSON_FILE = Path(__file__).parent / "hotel_state.json"


class HotelError(Exception):
    pass


class Hotel:
    """глaвный контроллер системы отеля"""

    def __init__(self, name: str = "MyHotel", db_path: str = None, notifier: Optional[NotificationService] = None):
        db.init_db(db_path)
        self.name = name
        self.db_path = db_path
        self.notifier = notifier
        self.load_json()

    # JSON методы
    def save_json(self):
        """сохраняет актуальные данные в JSON"""
        data = {
            "name": self.name,
            "rooms": [r.to_dict() for r in self.list_rooms()],
            "guests": [g.to_dict() for g in self._load_all_guests()],
            "bookings": [b.to_dict() for b in self.list_bookings()],
            "payments": self._load_all_payments()
        }
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_json(self):
        """загружает данные из JSON в базу данных"""
        if not JSON_FILE.exists():
            return
        
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                return

        for r in data.get("rooms", []):
            try:
                self.add_room(Room.from_dict(r))
            except (HotelError, Exception):
                pass

        for g in data.get("guests", []):
            try:
                self.register_guest(Guest.from_dict(g))
            except (HotelError, Exception):
                pass

        for b in data.get("bookings", []):
            try:
                booking = Booking.from_dict(b)
                self._execute_sql("""
                    INSERT OR IGNORE INTO bookings 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (booking.booking_id, booking.guest_id, booking.room_number,
                      booking.check_in_date.isoformat(), booking.check_out_date.isoformat(), 
                      booking.status))
            except Exception:
                pass

        for p in data.get("payments", []):
            try:
                self._execute_sql("""
                    INSERT OR IGNORE INTO payments 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (p.get("payment_id"), p.get("booking_id"), p.get("amount"),
                      p.get("payment_date"), p.get("payment_method"), 
                      p.get("status"), p.get("transaction_id")))
            except Exception:
                pass

    # вспомогательные методы для базы данных
    def _execute_sql(self, query: str, params: tuple = ()):
        """выполняет SQL запрос с параметрами"""
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        conn.close()

    def _fetch_one(self, query: str, params: tuple = ()):
        """выполняет запрос и возвращает одну строку"""
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        conn.close()
        return row

    def _fetch_all(self, query: str, params: tuple = ()):
        """выполняет запрос и возвращает все строки"""
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return rows

    def _load_all_payments(self) -> List[Dict[str, Any]]:
        rows = self._fetch_all("SELECT * FROM payments")
        return [{
            "payment_id": r[0], "booking_id": r[1], "amount": r[2],
            "payment_date": r[3], "payment_method": r[4], 
            "status": r[5], "transaction_id": r[6]
        } for r in rows]

    def _load_all_guests(self) -> List[Guest]:
        rows = self._fetch_all("SELECT * FROM guests")
        return [Guest(*r) for r in rows]

    # комнаты
    def add_room(self, room: Room):
        """Ддбавляет комнату в БД"""
        try:
            self._execute_sql(
                "INSERT INTO rooms VALUES (?, ?, ?, ?)",
                (room.room_number, room.room_type, room.price_per_night, int(room.is_occupied))
            )
            self.save_json()
        except sqlite3.IntegrityError:
            raise HotelError(f"Комната {room.room_number} уже существует.")

    def remove_room(self, room_number: str):
        """удаляет комнату"""
        self._execute_sql("DELETE FROM rooms WHERE room_number = ?", (room_number,))
        self.save_json()

    def find_room(self, room_number: str) -> Optional[Room]:
        """находит комнату по номеру"""
        row = self._fetch_one("SELECT * FROM rooms WHERE room_number = ?", (room_number,))
        return Room(*row) if row else None

    def list_rooms(self) -> List[Room]:
        """возвращает список всех комнат"""
        rows = self._fetch_all("SELECT * FROM rooms")
        return [Room(*r) for r in rows]

    # Гости
    def register_guest(self, guest: Guest):
        """регистрирует гостя"""
        try:
            self._execute_sql("INSERT INTO guests VALUES (?, ?, ?, ?)",
                             (guest.guest_id, guest.name, guest.email, guest.phone))
            self.save_json()
        except sqlite3.IntegrityError:
            raise HotelError(f"Гость {guest.guest_id} уже зарегистрирован.")

    def find_guest(self, guest_id: str) -> Optional[Guest]:
        """находит гостя по ID"""
        row = self._fetch_one("SELECT * FROM guests WHERE guest_id = ?", (guest_id,))
        return Guest(*row) if row else None

    # Бронирования
    def _overlaps(self, start1: date, end1: date, start2: date, end2: date) -> bool:
        """проверяет пересечение дат"""
        return start1 < end2 and start2 < end1

    def _room_has_conflict(self, room_number: str, check_in: date, check_out: date) -> bool:
        """проверяет занята ли комната в указанный период"""
        rows = self._fetch_all(
            "SELECT check_in_date, check_out_date, status FROM bookings WHERE room_number = ?",
            (room_number,)
        )
        for check_in_str, check_out_str, status in rows:
            if status in ("cancelled", "checked_out"):
                continue
            existing_in = date.fromisoformat(check_in_str)
            existing_out = date.fromisoformat(check_out_str)
            if self._overlaps(check_in, check_out, existing_in, existing_out):
                return True
        return False

    def create_booking(self, guest_id: str, room_number: str, check_in: date, check_out: date) -> Booking:
        """создает бронирование"""
        if check_out <= check_in:
            raise HotelError("Дата выезда должна быть позже даты заезда.")
        
        if not self.find_guest(guest_id):
            raise HotelError("Гость не найден.")
        
        if not self.find_room(room_number):
            raise HotelError("Комната не найдена.")
        
        if self._room_has_conflict(room_number, check_in, check_out):
            raise HotelError("Комната занята в указанный период.")
        
        booking_id = str(uuid.uuid4())
        self._execute_sql(
            "INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?)",
            (booking_id, guest_id, room_number, check_in.isoformat(), 
             check_out.isoformat(), "booked")
        )
        self.save_json()
        
        # отправляем уведомление пользователю
        guest = self.find_guest(guest_id)
        if self.notifier and guest and guest.email:
            try:
                self.notifier.send_booking_confirmation(guest.email, booking_id)
            except Exception:
                pass
        
        return Booking(booking_id, guest_id, room_number, check_in, check_out, "booked")

    def cancel_booking(self, booking_id: str):
        """отменяет бронирование"""
        row = self._fetch_one("SELECT status, guest_id FROM bookings WHERE booking_id = ?", (booking_id,))
        if not row:
            raise HotelError("Бронь не найдена.")
        
        status, guest_id = row
        if status in ("cancelled", "checked_out"):
            raise HotelError("Невозможно отменить уже завершённую или отменённую бронь.")
        
        self._execute_sql("UPDATE bookings SET status = ? WHERE booking_id = ?", ("cancelled", booking_id))
        self.save_json()
        
        # отправляем уведомление пользователю
        guest = self.find_guest(guest_id)
        if guest and self.notifier:
            try:
                self.notifier.send_booking_cancellation(guest.email, booking_id)
                if guest.phone:
                    self.notifier.send_sms_notification(guest.phone, f"Бронь {booking_id} отменена")
            except Exception:
                pass

    def find_booking(self, booking_id: str) -> Optional[Booking]:
        """находит бронирование по ID"""
        row = self._fetch_one("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
        if row:
            return Booking(row[0], row[1], row[2], 
                          date.fromisoformat(row[3]), 
                          date.fromisoformat(row[4]), 
                          row[5])
        return None

    def check_in(self, booking_id: str, today: date):
        """заселение гостя"""
        booking = self.find_booking(booking_id)
        if not booking:
            raise HotelError("Бронь не найдена.")
        
        if booking.status != "booked":
            raise HotelError("Можно заселить только бронь в статусе 'booked'.")
        
        if booking.check_in_date != today:
            raise HotelError("Дата заселения не совпадает с текущей датой.")
        
        self._execute_sql("UPDATE bookings SET status = ? WHERE booking_id = ?", ("checked_in", booking_id))
        self._execute_sql("UPDATE rooms SET is_occupied = ? WHERE room_number = ?", (1, booking.room_number))
        self.save_json()
        
        # отправляем уведомление пользователю
        guest = self.find_guest(booking.guest_id)
        if self.notifier and guest:
            try:
                self.notifier.send_checkin_reminder(guest.email, booking_id)
                if guest.phone:
                    self.notifier.send_sms_notification(guest.phone, f"Вы заселены в комнату {booking.room_number}")
            except Exception:
                pass

    def check_out(self, booking_id: str, today: date) -> float:
        """выселение гостя"""
        booking = self.find_booking(booking_id)
        if not booking:
            raise HotelError("Бронь не найдена.")
        
        if booking.status != "checked_in":
            raise HotelError("Можно выселить только бронь в статусе 'checked_in'.")
        
        if booking.check_out_date != today:
            raise HotelError("Дата выселения не совпадает с текущей датой.")
        
        room = self.find_room(booking.room_number)
        if not room:
            raise HotelError("Комната для брони не найдена.")
        
        nights = (booking.check_out_date - booking.check_in_date).days
        total = nights * room.price_per_night
        
        self._execute_sql("UPDATE bookings SET status = ? WHERE booking_id = ?", ("checked_out", booking_id))
        self._execute_sql("UPDATE rooms SET is_occupied = ? WHERE room_number = ?", (0, booking.room_number))
        
        # обработка платежа
        self.process_payment(booking_id, total, "card")
        self.save_json()
        
        # отправляем уведомления пользователю
        guest = self.find_guest(booking.guest_id)
        if self.notifier and guest:
            try:
                self.notifier.send_checkout_reminder(guest.email, booking_id)
                if guest.phone:
                    self.notifier.send_sms_notification(guest.phone, f"Вы выселены, сумма {total}")
            except Exception:
                pass
        
        return total

    def list_bookings(self) -> List[Booking]:
        """возвращает список всех бронирований"""
        rows = self._fetch_all("SELECT * FROM bookings")
        return [Booking(row[0], row[1], row[2], 
                       date.fromisoformat(row[3]), 
                       date.fromisoformat(row[4]), 
                       row[5]) for row in rows]

    # Вспомогательные методы
    def get_available_rooms(self, check_in: date, check_out: date) -> List[Room]:
        """возвращает список свободных комнат на период"""
        return [room for room in self.list_rooms() 
                if not self.check_room_availability(room.room_number, check_in, check_out)]

    def check_room_availability(self, room_number: str, check_in: date, check_out: date) -> bool:
        """проверяет доступность комнаты (True = занята)"""
        return self._room_has_conflict(room_number, check_in, check_out)

    def validate_booking_dates(self, check_in: date, check_out: date):
        """проверяет корректность дат бронирования"""
        if check_out <= check_in:
            raise HotelError("Дата выезда должна быть строго позже даты заезда.")

    # Платежи
    def process_payment(self, booking_id: str, amount: float, payment_method: str = "card") -> Payment:
        """орабатываем платеж"""
        payment = Payment(booking_id=booking_id, amount=amount, payment_method=payment_method)
        payment.process_payment()
        
        self._execute_sql(
            "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?)",
            (payment.payment_id, payment.booking_id, payment.amount,
             payment.payment_date, payment.payment_method, 
             payment.status, payment.transaction_id)
        )
        
        # отправляем уведомление пользователю
        booking = self.find_booking(booking_id)
        if booking:
            guest = self.find_guest(booking.guest_id)
            if self.notifier and guest and guest.email:
                try:
                    self.notifier.send_payment_confirmation(guest.email, payment.get_payment_details())
                except Exception:
                    pass
        
        return payment

    def get_payment_history(self, guest_id: str) -> List[Dict[str, Any]]:
        """возвращает историю платежей гостя"""
        payments = []
        rows = self._fetch_all("SELECT booking_id FROM bookings WHERE guest_id = ?", (guest_id,))
        for (booking_id,) in rows:
            payment_rows = self._fetch_all("SELECT * FROM payments WHERE booking_id = ?", (booking_id,))
            for p in payment_rows:
                payments.append({
                    "payment_id": p[0], "booking_id": p[1], "amount": p[2],
                    "payment_date": p[3], "payment_method": p[4],
                    "status": p[5], "transaction_id": p[6]
                })
        return payments