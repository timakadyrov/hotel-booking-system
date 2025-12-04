"""
payment.py
Модель платежа и простая заглушка процессора платежей
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Payment:
    payment_id: str
    booking_id: str
    amount: float
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    status: str = "pending"  # pending, completed, refunded
    transaction_id: Optional[str] = None

    def __init__(self, booking_id: str, amount: float, payment_method: Optional[str] = None):
        self.payment_id = str(uuid.uuid4())
        self.booking_id = booking_id
        self.amount = amount
        self.payment_date = None
        self.payment_method = payment_method
        self.status = "pending"
        self.transaction_id = None

    def process_payment(self):
        """Имитация обработки платежа."""
        self.status = "completed"
        self.payment_date = datetime.now().isoformat()
        self.transaction_id = str(uuid.uuid4())
        return self

    def confirm_payment(self):
        self.status = "confirmed"
        return self

    def issue_refund(self):
        self.status = "refunded"
        return self

    def get_payment_details(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "booking_id": self.booking_id,
            "amount": self.amount,
            "payment_date": self.payment_date,
            "payment_method": self.payment_method,
            "status": self.status,
            "transaction_id": self.transaction_id
        }

    def is_successful(self) -> bool:
        return self.status in ("completed", "confirmed")
