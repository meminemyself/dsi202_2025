import qrcode
import base64
from io import BytesIO
from crcmod.predefined import mkCrcFun

def format_mobile(number: str) -> str:
    number = number.strip().replace("-", "").replace(" ", "")
    if number.startswith("0"):
        number = "66" + number[1:]
    return number

def generate_promptpay_payload(phone_number: str, amount: float) -> str:
    phone = format_mobile(phone_number)
    amt_str = f"{amount:.2f}"
    amt_len = len(amt_str)

    payload = (
        "000201"                              # Payload format
        "010211"                              # Static QR
        "29370016A000000677010111"           # Application ID
        f"011300{phone}"                      # Merchant phone
        "5303764"                             # Currency (THB)
        f"54{amt_len:02d}{amt_str}"          # Amount with 2 decimal
        "5802TH"                              # Country
        "6304"                                # CRC Placeholder
    )

    crc16 = mkCrcFun('crc-ccitt-false')
    crc = format(crc16(payload.encode('utf-8')), '04X')
    return payload + crc

def generate_qr_base64(phone_number: str, amount: float) -> str:
    payload = generate_promptpay_payload(phone_number, amount)
    qr = qrcode.make(payload)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()