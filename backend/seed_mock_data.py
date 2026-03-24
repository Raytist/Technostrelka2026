from app.db.database import SessionLocal
from app.models.subscription import Subscriptions
from app.models.parsed_receipt import ParsedReceipts
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

USER_ID = "05b99393-19ae-45c5-adff-b194361a8e04"

def seed():
    db = SessionLocal()
    try:
        # Clear existing for this user to avoid duplicates if rerun
        db.query(Subscriptions).filter(Subscriptions.user_id == USER_ID).delete()
        db.query(ParsedReceipts).filter(ParsedReceipts.user_id == USER_ID).delete()

        # 1. Add Subscriptions
        subs = [
            {"name": "Netflix", "amount": 1199, "status": "active", "cat": "Кино и музыка"},
            {"name": "Яндекс Плюс", "amount": 299, "status": "active", "cat": "Сервисы"},
            {"name": "Бусти", "amount": 500, "status": "active", "cat": "Сервисы"},
            {"name": "Тинькофф Премиум", "amount": 1990, "status": "active", "cat": "Финансы"},
            {"name": "Spotify", "amount": 169, "status": "active", "cat": "Кино и музыка"},
        ]

        now = datetime.utcnow()
        for s in subs:
            sub = Subscriptions(
                user_id=USER_ID,
                name=s["name"],
                raw_merchant_name=s["name"].upper(),
                amount=Decimal(s["amount"]),
                status=s["status"],
                periodicity="monthly",
                next_payment_date=now + timedelta(days=15)
            )
            db.add(sub)

        # 2. Add Receipt History (6 months)
        for i in range(6):
            month_date = now - timedelta(days=i * 30)
            # Add receipts for each sub for that month
            for s in subs:
                # Add some randomness to history (previous months had slightly different prices or some were missing)
                if i > 3 and s["name"] == "Netflix": continue # Netflix started 3 months ago
                
                receipt = ParsedReceipts(
                    user_id=USER_ID,
                    message_id=str(uuid.uuid4()),
                    amount=Decimal(s["amount"]),
                    merchant_name=s["name"],
                    receipt_date=month_date - timedelta(days=2),
                    is_trial=False
                )
                db.add(receipt)

        db.commit()
        print(f"Successfully seeded mock data for user {USER_ID}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
