from celery import shared_task
from sqlalchemy.orm import Session
import re
from bs4 import BeautifulSoup

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    from app.core.config import settings
    # Initialize Firebase Admin globally for Celery workers
    try:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass # Already initialized
    except Exception as e:
        print(f"Warning: Firebase not configured properly ({e})")
except ImportError:
    pass

from datetime import datetime, timedelta, timezone
import imaplib
import email
import socket
from email.policy import default
from dateutil.relativedelta import relativedelta

from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.user import Users
from app.models.yandex_connection import YandexConnections
from app.models.parsed_receipt import ParsedReceipts
from app.models.subscription import Subscriptions
from app.core.security import decrypt_token
from app.core.mail_parser import parse_receipt

def generate_oauth2_string(username, access_token, base64_encode=False):
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (username, access_token)
    if base64_encode:
        import base64
        return base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    return auth_string

@celery_app.task
def mail_fetch_task(user_id: str):
    """
    Connects to Yandex IMAP, fetches unseen emails.
    """
    db = SessionLocal()
    try:
        conn = db.query(YandexConnections).filter(YandexConnections.user_id == user_id).first()
        if not conn:
            return "No Yandex connection found."
            
        access_token = decrypt_token(conn.access_token)
        
        try:
            # Set timeout for socket operations
            socket.setdefaulttimeout(20)
            mail = imaplib.IMAP4_SSL('imap.yandex.ru')
            # Increase reliability of login
            try:
                mail.authenticate('XOAUTH2', lambda x: generate_oauth2_string(conn.email, access_token).encode('utf-8'))
            except imaplib.IMAP4.error as e:
                print(f"IMAP Auth Error for user {user_id}: {e}")
                return f"Auth failure: {e}"
                
            mail.select("INBOX")
            
            # Fetch messages after last_sync_uid. 
            # If not synced before, fetch recent 100 or UNSEEN. 
            # For simplicity, fetching all UNSEEN here.
            status, messages = mail.search(None, 'UNSEEN')
            
            if status == 'OK':
                unseen_ids = messages[0].split()
                # For safety and speed, only process the last 10 incoming emails in one batch
                for num in unseen_ids[-10:]:
                    # Instead of parsing everything here, pass id
                    status, msg_data = mail.fetch(num, '(BODY.PEEK[])')
                    if status == "OK":
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email, policy=default)
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() in ["text/plain", "text/html"]:
                                    body += part.get_payload(decode=True).decode(errors="ignore")
                        else:
                            body = msg.get_payload(decode=True).decode(errors="ignore")
                            
                        message_id = msg.get("Message-ID", f"unknown-{num}")
                        
                        # Trigger parsing task async
                        receipt_parse_task.delay(user_id, message_id, body)
                    
            mail.logout()
        except Exception as e:
            # Handle IMAP failures (e.g. token expired)
            print(f"IMAP Error: {e}")
            
    finally:
        db.close()
    return "Mail fetch complete"


@celery_app.task
def receipt_parse_task(user_id: str, message_id: str, email_content: str):
    """
    Parses regex to find merchant and amount. 
    Writes to ParsedReceipts table, then triggers matcher.
    """
    db = SessionLocal()
    try:
        # Avoid duplicate parsing
        existing = db.query(ParsedReceipts).filter(ParsedReceipts.message_id == message_id).first()
        if existing:
            return "Already parsed"
            
        data = parse_receipt(email_content)
        if data and data['merchant_name'] and data['amount']:
            receipt = ParsedReceipts(
                user_id=user_id,
                message_id=message_id,
                amount=data['amount'],
                merchant_name=data['merchant_name'],
                is_trial=data.get('is_trial', False),
                receipt_date=datetime.now(timezone.utc)
            )
            db.add(receipt)
            db.commit()
            
            # Trigger matcher logic
            subscriptions_matcher_task.delay(user_id)
            return "Parsed and saved"
            
    finally:
        db.close()
    return "Parse failed or ignored"
    

@celery_app.task
def subscriptions_matcher_task(user_id: str):
    """
    Processing receipts for user.
    """
    db = SessionLocal()
    try:
        receipts = db.query(ParsedReceipts).filter(ParsedReceipts.user_id == user_id).all()
        
        # Group by merchant
        merchants = {}
        for r in receipts:
            m = r.merchant_name.upper()
            if m not in merchants:
                merchants[m] = []
            merchants[m].append(r)
            
        for merchant, txs in merchants.items():
            txs = sorted(txs, key=lambda x: x.receipt_date)
            # Check if subscription already exists for this merchant
            existing_sub = db.query(Subscriptions).filter(
                Subscriptions.user_id == user_id,
                Subscriptions.raw_merchant_name == merchant
            ).first()
            
            if existing_sub:
                continue
                
            # Rule 1: Multi-transaction -> assume subscription
            if len(txs) >= 2:
                # generate generic subscription
                sub = Subscriptions(
                    user_id=user_id,
                    raw_merchant_name=merchant,
                    name=merchant,
                    amount=txs[-1].amount,
                    status="unverified",
                    periodicity="monthly"
                )
                db.add(sub)
                db.commit()
                continue
                
            # Rule 2: Single transaction checking sizes
            if len(txs) == 1:
                tx = txs[0]
                amount = tx.amount
                
                # Check for micro-charge trial (0.5 to 15 rubles) or semantic trial keyword
                if 0.5 <= amount <= 15 or tx.is_trial:
                    sub = Subscriptions(
                        user_id=user_id,
                        raw_merchant_name=merchant,
                        name=f"{merchant} (Trial?)",
                        amount=amount,
                        status="unverified",
                        periodicity="monthly"
                    )
                    db.add(sub)
                    db.commit()
                    continue
                    
                # Exclude grocery / random non-round items based on rules
                excluded_keywords = ["ПЯТЕРОЧКА", "МАГНИТ", "АПТЕКА", "WILDBERRIES", "OZON", "ПЕРЕКРЕСТОК"]
                if any(kw in merchant for kw in excluded_keywords):
                    continue
                    
                # Requires round amounts for subscriptions (e.g. 199, 299). Ends in 9 or 0.
                if amount % 10 == 9 or amount % 10 == 0:
                    sub = Subscriptions(
                        user_id=user_id,
                        raw_merchant_name=merchant,
                        name=merchant,
                        amount=amount,
                        status="unverified",
                        periodicity="monthly"
                    )
                    db.add(sub)
                    db.commit()

    finally:
        db.close()
    return "Matcher complete"

@celery_app.task
def periodic_mail_sync():
    """
    Pulls all users who have active Yandex connections and triggers mail_fetch_task.
    Runs globally every 6 hours via Beat.
    """
    db = SessionLocal()
    try:
        connections = db.query(YandexConnections).all()
        for conn in connections:
            mail_fetch_task.delay(str(conn.user_id))
    finally:
        db.close()
    return "Periodic sync triggered"

@celery_app.task
def firebase_notifier_task():
    """
    Sends FCM Push notifications for upcoming payments.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        tomorrow = now + relativedelta(days=1)
        start_of_tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_tomorrow = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        subs_to_notify = db.query(Subscriptions, Users).join(Users, Subscriptions.user_id == Users.id).filter(
            Subscriptions.status.in_(["active", "trial", "custom"]),
            Subscriptions.next_payment_date >= start_of_tomorrow,
            Subscriptions.next_payment_date <= end_of_tomorrow,
            Users.push_enabled == True,
            Users.fcm_token.isnot(None)
        ).all()
        
        for sub, user in subs_to_notify:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="Подписка завтра 💳",
                        body=f"Завтра у вас спишется {sub.amount} руб за '{sub.name}'. Проверьте баланс!"
                    ),
                    token=user.fcm_token,
                )
                response = messaging.send(message)
                print(f"Successfully sent FCM push to {user.fcm_token}. ID: {response}")
            except Exception as e:
                print(f"Failed to send push to {user.fcm_token}: {str(e)}")
            
    finally:
        db.close()
    return "Notifier complete"
