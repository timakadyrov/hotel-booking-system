"""
main.py
Демонстрация сценариев: создаёт нескольких гостей, комнат и бронирований
Данные сохраняются в DB и hotel_state.json
"""

from datetime import date, timedelta
from models import Room, Guest
from hotel import Hotel, HotelError
from notification import EmailNotification

def demo():
    # создаём отель с email-уведомлениями
    h = Hotel(name="DemoHotel", notifier=EmailNotification())

    # добавляем комнаты (5 комнат)
    rooms = [
        Room("101", "single", 12000.0),
        Room("102", "double", 20000.0),
        Room("201", "suite", 45000.0),
        Room("202", "deluxe", 30000.0),
        Room("203", "deluxe", 30000.0),
    ]
    for r in rooms:
        try:
            h.add_room(r)
        except HotelError:
            pass

    # добавляем 5 гостей 
    # в JSON файле будут другие гости 
    guests = [
        Guest("g6", "Турсунов Халзат", "khalzat_tursunov@example.com", "+7707112299"),
        Guest("g2", "Мусабек Гульназ", "gulnazMusabek@example.com", "+77071213315"),
        Guest("g3", "Казбаев Акбар", "kazAkbar@example.com", "+77071124451"),
        Guest("g4", "Курлыков Глеб", "KyrlykovG@example.com", "+77058865233"),
        Guest("g5", "Ян Цзыхань", "YangZhihan@example.com", "+77071114617"),
    ]
    for g in guests:
        try:
            h.register_guest(g)
        except HotelError:
            pass

    today = date.today()
    bookings = []

    # обычные брони
    try:
        b1 = h.create_booking("g1", "101", today + timedelta(days=1), today + timedelta(days=3))
        bookings.append(b1)
    except HotelError as e:
        print("Ошибка при создании b1:", e)

    try:
        b2 = h.create_booking("g2", "102", today + timedelta(days=2), today + timedelta(days=5))
        bookings.append(b2)
    except HotelError as e:
        print("Ошибка при создании b2:", e)

    try:
        b3 = h.create_booking("g3", "201", today + timedelta(days=1), today + timedelta(days=2))
        bookings.append(b3)
    except HotelError as e:
        print("Ошибка при создании b3:", e)

    try:
        b4 = h.create_booking("g4", "202", today + timedelta(days=10), today + timedelta(days=12))
        bookings.append(b4)
    except HotelError as e:
        print("Ошибка при создании b4:", e)
        
    try:
        b6 = h.create_booking("g6", "203", today + timedelta(days=1), today + timedelta(days=2))
        bookings.append(b6)
    except HotelError as e:
        print("Ошибка при создании b6:", e)

    """
    попытка забронировать уже занятую комнату
    """
    
    print("\n Комната занята — отказ в бронировании")
    try:
        # g5 пытается забронировать 101, которая уже занята в этот период
        if not h.check_room_availability("101", today + timedelta(days=2), today + timedelta(days=4)):
            h.notifier.send_booking_cancellation(
                guests[4],  # g5
                "Комната 101 недоступна в выбранные даты."
            )
            print("ОТКАЗ: Комната занята, уведомление отправлено g5.")
        else:
            b_conflict = h.create_booking("g5", "101", today + timedelta(days=2), today + timedelta(days=4))
            bookings.append(b_conflict)
    except HotelError as e:
        print("Ошибка при попытке забронировать занятую комнату:", e)

    """
    Сценарий: выселение гостя
    """
    
    print("\nВыселение гостя (check-out)")
    try:
        # выселяем g1 из 101
        h.check_out("g1", "101")
        h.notifier.send_checkout_confirmation(guests[0], b1)
        print("Гость g1 успешно выселен, уведомление отправлено.")
    except HotelError as e:
        print("Ошибка при выселении:", e)

    """
    Сохраняем состояние в JSON
    """
    
    h.save_json()
    print("\nДемо-запись завершена. Комнаты, гости и брони сохранены в БД и hotel_state.json")

    # Показать все брони
    for b in h.list_bookings():
        print(b.to_dict())

    # Платёжная история пока пустая
    print("Payment history for g1:", h.get_payment_history("g1"))


if __name__ == "__main__":
    demo()
