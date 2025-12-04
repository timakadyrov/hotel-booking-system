"""
hotel.py
Логика управления отелем: добавление комнат, гостей, бронирования, check-in/out.
Реализованы методыL: add_room, remove_room, find_room, register_guest, find_guest,
create_booking, cancel_booking, check_in, check_out, get_available_rooms, validate_booking_dates,
check_room_availability, process_payment, get_payment_history.
Сохраняет данные в нашу БД и файл json
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
    """Класс отеля — главный контроллер системы."""

    def __init__(self, name: str = "MyHotel", db_path: str = None, notifier: Optional[NotificationService] = None):
        db.init_db(db_path)
        self.name = name
        self.db_path = db_path
        self.notifier = notifier

        # при старте загружаем json (если есть) - и записываем в БД
        self.load_json()

    # JSON

    def save_json(self):
        """Сохраняет в hotel_state.json актуальные данные из БД."""
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
        """Если JSON-файл есть — загружает его содержимое в БД (insert-ignore)."""
        if not JSON_FILE.exists():
            return
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                return

        # load rooms
        for r in data.get("rooms", []):
            try:
                room = Room.from_dict(r)
                try:
                    self.add_room(room)
                except HotelError:
                    pass
            except Exception:
                pass

        # load guests
        for g in data.get("guests", []):
            try:
                guest = Guest.from_dict(g)
                try:
                    self.register_guest(guest)
                except HotelError:
                    pass
            except Exception:
                pass

        # load bookings
        for b in data.get("bookings", []):
            try:
                booking = Booking.from_dict(b)
                # insert raw
                self._insert_booking_raw(booking)
            except Exception:
                pass

        # load payments (we'll insert if present)
        for p in data.get("payments", []):
            try:
                self._insert_payment_raw(p)
            except Exception:
                pass

    def _insert_booking_raw(self, booking: Booking):
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO bookings
            (booking_id, guest_id, room_number, check_in_date, check_out_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            booking.booking_id,
            booking.guest_id,
            booking.room_number,
            booking.check_in_date.isoformat(),
            booking.check_out_date.isoformat(),
            booking.status
        ))
        conn.commit()
        conn.close()

    def _insert_payment_raw(self, p: Dict[str, Any]):
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO payments
            (payment_id, booking_id, amount, payment_date, payment_method, status, transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            p.get("payment_id"),
            p.get("booking_id"),
            p.get("amount"),
            p.get("payment_date"),
            p.get("payment_method"),
            p.get("status"),
            p.get("transaction_id")
        ))
        conn.commit()
        conn.close()

    def _load_all_payments(self) -> List[Dict[str, Any]]:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT payment_id, booking_id, amount, payment_date, payment_method, status, transaction_id FROM payments")
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            res.append({
                "payment_id": r[0],
                "booking_id": r[1],
                "amount": r[2],
                "payment_date": r[3],
                "payment_method": r[4],
                "status": r[5],
                "transaction_id": r[6]
            })
        return res

    def _load_all_guests(self) -> List[Guest]:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT guest_id, name, email, phone FROM guests")
        rows = cur.fetchall()
        conn.close()
        return [Guest(*r) for r in rows]

    # Rooms 

    def add_room(self, room: Room):
        """Добавить комнату в БД."""
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO rooms(room_number, room_type, price_per_night, is_occupied) VALUES (?, ?, ?, ?)",
                (room.room_number, room.room_type, room.price_per_night, int(room.is_occupied))
            )
            conn.commit()
            self.save_json()
        except sqlite3.IntegrityError:
            raise HotelError(f"Комната с номером {room.room_number} уже существует.")
        finally:
            conn.close()

    def remove_room(self, room_number: str):
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM rooms WHERE room_number = ?", (room_number,))
        conn.commit()
        conn.close()
        self.save_json()

    def find_room(self, room_number: str) -> Optional[Room]:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT room_number, room_type, price_per_night, is_occupied FROM rooms WHERE room_number = ?",
                    (room_number,))
        row = cur.fetchone()
        conn.close()
        if row:
            return Room(*row)
        return None

    def list_rooms(self) -> List[Room]:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT room_number, room_type, price_per_night, is_occupied FROM rooms")
        rows = cur.fetchall()
        conn.close()
        return [Room(*r) for r in rows]

    def get_available_rooms(self, check_in: date, check_out: date) -> List[Room]:
        """Возвращает список свободных комнат на период."""
        rooms = self.list_rooms()
        available = []
        for room in rooms:
            if not self.check_room_availability(room.room_number, check_in, check_out):
                # check_room_availability возвращает True если есть конфликт
                available.append(room)
        return available

    def validate_booking_dates(self, check_in: date, check_out: date):
        """Обертка для валидации дат."""
        if check_out <= check_in:
            raise HotelError("Дата выезда должна быть строго позже даты заезда.")

    def check_room_availability(self, room_number: str, check_in: date, check_out: date) -> bool:
        """Возвращает True если комната ЗАНЯТА (есть конфликт)."""
        return self._room_has_conflict(room_number, check_in, check_out)

    # Guests 

    def register_guest(self, guest: Guest):
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO guests(guest_id, name, email, phone) VALUES (?, ?, ?, ?)",
                        (guest.guest_id, guest.name, guest.email, guest.phone))
            conn.commit()
            self.save_json()
        except sqlite3.IntegrityError:
            raise HotelError(f"Гость с id {guest.guest_id} уже зарегистрирован.")
        finally:
            conn.close()

    def find_guest(self, guest_id: str) -> Optional[Guest]:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT guest_id, name, email, phone FROM guests WHERE guest_id = ?", (guest_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return Guest(*row)
        return None

    # Bookings

    def _overlaps(self, start1: date, end1: date, start2: date, end2: date) -> bool:
        """Проверка пересечения отрезков дат [start, end)."""
        return start1 < end2 and start2 < end1

    def _validate_dates(self, check_in: date, check_out: date):
        if check_out <= check_in:
            raise HotelError("Дата выезда должна быть строго позже даты заезда.")

    def _room_has_conflict(self, room_number: str, check_in: date, check_out: date) -> bool:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT check_in_date, check_out_date, status FROM bookings WHERE room_number = ?",
                    (room_number,))
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            existing_in = date.fromisoformat(r[0])
            existing_out = date.fromisoformat(r[1])
            status = r[2]
            if status in ("cancelled", "checked_out"):
                continue
            if self._overlaps(check_in, check_out, existing_in, existing_out):
                return True
        return False

    def create_booking(self, guest_id: str, room_number: str, check_in: date, check_out: date) -> Booking:
        """Создать бронь при отсутствии конфликтов и наличии гостя/комнаты."""
        self._validate_dates(check_in, check_out)
        guest = self.find_guest(guest_id)
        if guest is None:
            raise HotelError("Гость не найден.")
        room = self.find_room(room_number)
        if room is None:
            raise HotelError("Комната не найдена.")
        if self._room_has_conflict(room_number, check_in, check_out):
            raise HotelError("Комната занята в указанный период (конфликт дат).")
        booking_id = str(uuid.uuid4())
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""INSERT INTO bookings(booking_id, guest_id, room_number, check_in_date, check_out_date, status)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (booking_id, guest_id, room_number, check_in.isoformat(), check_out.isoformat(), "booked"))
        conn.commit()
        conn.close()
        self.save_json()
        if self.notifier and guest.email:
            try:
                self.notifier.send_booking_confirmation(guest.email, booking_id)
            except Exception:
                pass
        return Booking(booking_id, guest_id, room_number, check_in, check_out, "booked")

    def cancel_booking(self, booking_id: str):
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT status, guest_id FROM bookings WHERE booking_id = ?", (booking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise HotelError("Бронь не найдена.")
        status = row[0]
        guest_id = row[1]
        if status in ("cancelled", "checked_out"):
            conn.close()
            raise HotelError("Невозможно отменить уже завершённую или отменённую бронь.")
        cur.execute("UPDATE bookings SET status = ? WHERE booking_id = ?", ("cancelled", booking_id))
        conn.commit()
        conn.close()
        self.save_json()
        guest = self.find_guest(guest_id)
        if guest and self.notifier:
            try:
                # отправляем и email и sms
                self.notifier.send_booking_cancellation(guest.email, booking_id)
                self.notifier.send_sms_notification(guest.phone, f"Ваша бронь {booking_id} отменена")
            except Exception:
                pass

    def find_booking(self, booking_id: str) -> Optional[Booking]:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT booking_id, guest_id, room_number, check_in_date, check_out_date, status FROM bookings WHERE booking_id = ?",
                    (booking_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return Booking(row[0], row[1], row[2], date.fromisoformat(row[3]), date.fromisoformat(row[4]), row[5])
        return None

    def check_in(self, booking_id: str, today: date):
        """Заселение — перевод броня->checked_in и пометка комнаты занятой.
        Упрощённая проверка даты: today == check_in_date.
        """
        booking = self.find_booking(booking_id)
        if booking is None:
            raise HotelError("Бронь не найдена.")
        if booking.status != "booked":
            raise HotelError("Можно заселить только бронь в статусе 'booked'.")
        if booking.check_in_date != today:
            raise HotelError("Дата заселения не совпадает с текущей датой.")
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE bookings SET status = ? WHERE booking_id = ?", ("checked_in", booking_id))
        cur.execute("UPDATE rooms SET is_occupied = ? WHERE room_number = ?", (1, booking.room_number))
        conn.commit()
        conn.close()
        self.save_json()
        guest = self.find_guest(booking.guest_id)
        if self.notifier:
            try:
                self.notifier.send_checkin_reminder(guest.email, booking_id)
                self.notifier.send_sms_notification(guest.phone, f"Вы заселены в комнату {booking.room_number}")
            except Exception:
                pass

    def check_out(self, booking_id: str, today: date) -> float:
        """Выселение — завершение брони, освобождение комнаты, подсчёт стоимости."""
        booking = self.find_booking(booking_id)
        if booking is None:
            raise HotelError("Бронь не найдена.")
        if booking.status != "checked_in":
            raise HotelError("Можно выселить только бронь в статусе 'checked_in'.")
        if booking.check_out_date != today:
            raise HotelError("Дата выселения не совпадает с текущей датой.")
        room = self.find_room(booking.room_number)
        if room is None:
            raise HotelError("Комната для брони не найдена.")
        nights = (booking.check_out_date - booking.check_in_date).days
        total = nights * room.price_per_night
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE bookings SET status = ? WHERE booking_id = ?", ("checked_out", booking_id))
        cur.execute("UPDATE rooms SET is_occupied = ? WHERE room_number = ?", (0, booking.room_number))
        conn.commit()
        conn.close()
        # process payment automatically (simple)
        payment = self.process_payment(booking_id, total, payment_method="card")
        self.save_json()
        guest = self.find_guest(booking.guest_id)
        if self.notifier:
            try:
                self.notifier.send_checkout_reminder(guest.email, booking_id)
                self.notifier.send_payment_confirmation(guest.email, payment.get_payment_details())
                self.notifier.send_sms_notification(guest.phone, f"Вы выселены, сумма {total}")
            except Exception:
                pass
        return total

    def list_bookings(self) -> List[Booking]:
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT booking_id, guest_id, room_number, check_in_date, check_out_date, status FROM bookings")
        rows = cur.fetchall()
        conn.close()
        bookings = []
        for row in rows:
            bookings.append(
                Booking(
                    booking_id=row[0],
                    guest_id=row[1],
                    room_number=row[2],
                    check_in_date=date.fromisoformat(row[3]),
                    check_out_date=date.fromisoformat(row[4]),
                    status=row[5]
                )
            )
        return bookings

    # ---------------- Payments ----------------

    def process_payment(self, booking_id: str, amount: float, payment_method: str = "card") -> Payment:
        """Простой процессинг платежа: создаём запись, помечаем completed."""
        payment = Payment(booking_id=booking_id, amount=amount, payment_method=payment_method)
        payment.process_payment()
        # сохраняем в БД
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payments(payment_id, booking_id, amount, payment_date, payment_method, status, transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            payment.payment_id,
            payment.booking_id,
            payment.amount,
            payment.payment_date,
            payment.payment_method,
            payment.status,
            payment.transaction_id
        ))
        conn.commit()
        conn.close()
        # уведомление
        booking = self.find_booking(booking_id)
        guest = None
        if booking:
            guest = self.find_guest(booking.guest_id)
        if self.notifier and guest:
            try:
                self.notifier.send_payment_confirmation(guest.email, payment.get_payment_details())
            except Exception:
                pass
        return payment

    def get_payment_history(self, guest_id: str) -> List[Dict[str, Any]]:
        """Возвращает список платежей для всех бронирований гостя."""
        conn = db.get_connection(self.db_path)
        cur = conn.cursor()
        # получаем booking_id для гостя
        cur.execute("SELECT booking_id FROM bookings WHERE guest_id = ?", (guest_id,))
        rows = cur.fetchall()
        payments = []
        for r in rows:
            bid = r[0]
            cur.execute("SELECT payment_id, booking_id, amount, payment_date, payment_method, status, transaction_id FROM payments WHERE booking_id = ?", (bid,))
            prow = cur.fetchall()
            for p in prow:
                payments.append({
                    "payment_id": p[0],
                    "booking_id": p[1],
                    "amount": p[2],
                    "payment_date": p[3],
                    "payment_method": p[4],
                    "status": p[5],
                    "transaction_id": p[6]
                })
        conn.close()
        return payments
