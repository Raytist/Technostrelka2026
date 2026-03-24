import re
from typing import Optional, Dict, Any
from decimal import Decimal
from bs4 import BeautifulSoup

def parse_receipt(email_content: str) -> Optional[Dict[str, Any]]:
    """
    Parses email body (HTML or plain text) to extract receipt details.
    Expected output: {"merchant_name": str, "amount": Decimal}
    """
    soup = BeautifulSoup(email_content, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    
    # 1. Look for Yandex / OFD typical receipt markers
    # Typical OFD receipt has "Сумма:" or "Итог:" followed by amount
    # and merchant name somewhere like "ООО РОМАШКА" or inside specific tags.
    
    amount = None
    merchant_name = None
    
    # Simple regex for amount (e.g., Сумма: 149.00 руб, Итого: 299 ₽)
    amount_match = re.search(r"(?:Сумма|Итог[о]?|К оплате)\s*[:]?\s*(\d+[\.,]\d{2})\s*(?:руб|₽|rur|rub)", text, re.IGNORECASE)
    if amount_match:
        val = amount_match.group(1).replace(",", ".")
        try:
            amount = Decimal(val)
        except:
            pass
            
    # Simple regex for merchant (ООО "Имя", ИП Фамилия)
    merchant_match = re.search(r"(ООО\s+[\"«][^\"»]+[\"»]|ИП\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.)", text)
    if merchant_match:
        merchant_name = merchant_match.group(1).replace('«', '"').replace('»', '"')
        
    # Fallback for known services that might not use strict OOO/IP patterns in email subjects
    if not merchant_name:
        known_services = ["Яндекс.Плюс", "Spotify", "Netflix", "Амедиатека", "Ivi", "Okko", "VK Музыка", "Telegram Premium", "Apple", "Google"]
        for service in known_services:
            if service.lower() in text.lower():
                merchant_name = service
                break
                
    # Semantic check for trial phrases
    is_trial = False
    trial_keywords = ["пробный", "trial", "первый месяц", "бесплатн"]
    if any(kw in text.lower() for kw in trial_keywords):
        is_trial = True
                
    if amount and merchant_name:
        return {
            "merchant_name": merchant_name,
            "amount": amount,
            "is_trial": is_trial
        }
        
    return None
