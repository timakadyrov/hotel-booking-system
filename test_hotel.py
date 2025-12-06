import unittest
import tempfile
import os
import json
from datetime import date, timedelta
from pathlib import Path

from models import Room, Guest
from hotel import Hotel, HotelError


class TestHotel(unittest.TestCase):
    def setUp(self):
        """создаем временную БД перед каждым тестом"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        
        # создаем временный JSON файл для тестов
        self.temp_json = tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w')
        self.temp_json.write('{"rooms": [], "guests": [], "bookings": [], "payments": [], "name": "TestHotel"}')
        self.temp_json.close()
        
        # Мокаем JSON_FILE для этого отеля
        import hotel as hotel_module
        self.original_json_file = hotel_module.JSON_FILE
        hotel_module.JSON_FILE = Path(self.temp_json.name)
        
        # пересоздаем отель с обновленным JSON_FILE
        self.hotel = Hotel(name="TestHotel", db_path=self.db_path)
        
    def tearDown(self):
        """Удаляем временные файлы после теста"""
        self.temp_db.close()
        os.unlink(self.db_path)
        
        # восстанавливаем оригинальный JSON_FILE
        import hotel as hotel_module
        hotel_module.JSON_FILE = self.original_json_file
        
        # удаляем временный JSON файл
        os.unlink(self.temp_json.name)
    

    # получается мы спользуем уникальные номера с префиксом "test-" чтобы не конфликтовать с main.py
    
    def test_add_and_find_room(self):
        """тест добавления и поиска комнаты"""
        room = Room("test-210", "single", 12000.0)
        self.hotel.add_room(room)
        
        found = self.hotel.find_room("test-210")
        self.assertIsNotNone(found)
        self.assertEqual(found.room_number, "test-210")
        self.assertEqual(found.room_type, "single")
        self.assertEqual(found.price_per_night, 12000.0)
    
    def test_register_and_find_guest(self):
        """тест регистрации и поиска гостя"""
        guest = Guest("test-g9", "Алихан Бектаев", "alikhan@example.com", "+77011223344")
        self.hotel.register_guest(guest)
        
        found = self.hotel.find_guest("test-g9")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Алихан Бектаев")
    
    def test_duplicate_room_error(self):
        """тест ошибки при добавлении дублирующейся комнаты"""
        room = Room("test-215", "double", 20000.0)
        self.hotel.add_room(room)
        
        # вторая попытка добавить ту же комнату должна вызвать ошибку
        with self.assertRaises(HotelError):
            self.hotel.add_room(Room("test-215", "suite", 45000.0))
    
    def test_duplicate_guest_error(self):
        """тест ошибки при регистрации дублирующегося гостя"""
        guest = Guest("test-g10", "Айгерим Сапар", "aigerim@example.com")
        self.hotel.register_guest(guest)
        
        with self.assertRaises(HotelError):
            self.hotel.register_guest(Guest("test-g10", "Нурлан Каирбеков", "nurlan@example.com"))
    
    def test_create_booking_success(self):
        """тест успешной создания брони"""
        self.hotel.add_room(Room("test-220", "single", 12000.0))
        self.hotel.register_guest(Guest("test-g11", "Динара Жумабаева"))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        booking = self.hotel.create_booking("test-g11", "test-220", check_in, check_out)
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, "booked")
        self.assertEqual(booking.guest_id, "test-g11")
        self.assertEqual(booking.room_number, "test-220")
    
    def test_booking_invalid_dates(self):
        """тест создания брони с некорректными датами"""
        self.hotel.add_room(Room("test-225", "double", 20000.0))
        self.hotel.register_guest(Guest("test-g12", "Джурукбаев Зейнур"))
        
        check_in = date.today() + timedelta(days=5)
        check_out = check_in - timedelta(days=1)  # Неправильные даты
        
        with self.assertRaises(HotelError):
            self.hotel.create_booking("test-g12", "test-225", check_in, check_out)
    
    def test_booking_nonexistent_guest(self):
        """тест создания брони для несуществующего гостя"""
        self.hotel.add_room(Room("test-230", "suite", 45000.0))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        with self.assertRaises(HotelError):
            self.hotel.create_booking("nonexistent-guest", "test-230", check_in, check_out)
    
    def test_booking_nonexistent_room(self):
        """тест создания брони для несуществующей комнаты"""
        self.hotel.register_guest(Guest("test-g13", "Кадыров Тимур"))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        # используем номер которого точно нет
        with self.assertRaises(HotelError):
            self.hotel.create_booking("test-g13", "not-exist-999", check_in, check_out)
    
    def test_room_availability(self):
        """тест проверки доступности комнаты"""
        self.hotel.add_room(Room("test-235", "deluxe", 30000.0))
        self.hotel.register_guest(Guest("test-g14", "Мусабек Гульназ"))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        # сначала комната свободна
        self.assertFalse(self.hotel.check_room_availability("test-235", check_in, check_out))
        
        # бронируем
        self.hotel.create_booking("test-g14", "test-235", check_in, check_out)
        
        # теперь занята
        self.assertTrue(self.hotel.check_room_availability("test-235", check_in, check_out))
    
    def test_cancel_booking(self):
        """тест отмены брони"""
        self.hotel.add_room(Room("test-240", "suite", 45000.0))
        self.hotel.register_guest(Guest("test-g15", "Сания Амангельды"))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        booking = self.hotel.create_booking("test-g15", "test-240", check_in, check_out)
        self.hotel.cancel_booking(booking.booking_id)
        
        cancelled = self.hotel.find_booking(booking.booking_id)
        self.assertEqual(cancelled.status, "cancelled")
    
    def test_cancel_nonexistent_booking(self):
        """тестик отмены несуществующей брони"""
        with self.assertRaises(HotelError):
            self.hotel.cancel_booking("nonexistent")
    
    def test_check_in_out_flow(self):
        """тест заселения и выселения"""
        today = date.today()
        
        self.hotel.add_room(Room("test-245", "deluxe", 30000.0))
        self.hotel.register_guest(Guest("test-g16", "Бауыржан Калиев"))
        
        booking = self.hotel.create_booking("test-g16", "test-245", today, today + timedelta(days=2))
        
        # заселение
        self.hotel.check_in(booking.booking_id, today)
        checked_in = self.hotel.find_booking(booking.booking_id)
        self.assertEqual(checked_in.status, "checked_in")
        
        # выселение
        total = self.hotel.check_out(booking.booking_id, today + timedelta(days=2))
        checked_out = self.hotel.find_booking(booking.booking_id)
        self.assertEqual(checked_out.status, "checked_out")
        
        # рроверяем расчет (2 ночи по 30000)
        self.assertEqual(total, 60000.0)
    
    def test_multiple_rooms_availability(self):
        """тест доступности нескольких комнат"""
        rooms = [
            Room("test-250", "single", 12000.0),
            Room("test-251", "double", 20000.0),
            Room("test-252", "suite", 45000.0)
        ]
        for room in rooms:
            self.hotel.add_room(room)
        
        self.hotel.register_guest(Guest("test-g17", "Гаухар Нургалиева"))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        # асе 3 тестовые комнаты доступны
        available = self.hotel.get_available_rooms(check_in, check_out)
        self.assertEqual(len(available), 3)
        
        # бронируем одну
        self.hotel.create_booking("test-g17", "test-250", check_in, check_out)
        
        # остается 2 доступных
        available = self.hotel.get_available_rooms(check_in, check_out)
        self.assertEqual(len(available), 2)
    
    def test_process_payment(self):
        """тест обработки платежа"""
        self.hotel.add_room(Room("test-255", "deluxe", 30000.0))
        self.hotel.register_guest(Guest("test-g18", "Данияр Сагинтаев"))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        booking = self.hotel.create_booking("test-g18", "test-255", check_in, check_out)
        payment = self.hotel.process_payment(booking.booking_id, 60000.0, "card")
        
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, "completed")
    
    def test_payment_history(self):
        """ьест истории платежей"""
        self.hotel.add_room(Room("test-260", "suite", 45000.0))
        self.hotel.register_guest(Guest("test-g19", "Айсулу Шаяхметова"))
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        booking1 = self.hotel.create_booking("test-g19", "test-260", check_in, check_out)
        booking2 = self.hotel.create_booking("test-g19", "test-260", 
                                            check_in + timedelta(days=5), 
                                            check_out + timedelta(days=5))
        
        self.hotel.process_payment(booking1.booking_id, 90000.0, "card")
        self.hotel.process_payment(booking2.booking_id, 90000.0, "cash")
        
        history = self.hotel.get_payment_history("test-g19")
        self.assertEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()