import qrcode
import base64
from io import BytesIO
from typing import Optional
import re
import binascii

def format_phone(phone: str) -> str:
    phone = re.sub(r'\D', '', phone)  # remove non-digit
    if phone.startswith('0'):
        phone = '66' + phone[1:]
    return phone

def get_payload(phone: str, amount: Optional[float] = None) -> str:
    phone = format_phone(phone)
    payload = f"00020101021129370016A0000006770101110113{len(phone):02d}{phone}"
    if amount is not None:
        payload += f"540{len(f'{amount:.2f}'):02d}{amount:.2f}"
    payload += "5802TH53037646304"  # country code + currency + checksum placeholder
    crc = binascii.crc_hqx(payload.encode('utf-8'), 0xffff)
    payload += f"{crc:04X}"
    return payload

def generate_qr_base64(payload: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return qr_base64