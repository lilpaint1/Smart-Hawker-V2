"""ส่ง SMS แบบสลับผู้ให้บริการด้วย env SMS_PROVIDER
   console     = โชว์ใน terminal (dev, ฟรี)
   twilio      = Twilio (international, ต้องตั้ง TWILIO_* envs)
   thaibulksms = ThaiBulkSMS (ไทย, ต้องตั้ง THAIBULKSMS_KEY + THAIBULKSMS_SECRET)
   awssns      = AWS SNS (ต้องตั้ง AWS_* envs + pip install boto3)
"""
import os
import base64
import urllib.parse
import urllib.request


def send_sms(phone: str, text: str) -> dict:
    provider = os.environ.get("SMS_PROVIDER", "console").lower()
    if provider == "twilio":
        return _send_twilio(phone, text)
    if provider == "thaibulksms":
        return _send_thaibulksms(phone, text)
    if provider == "awssns":
        return _send_awssns(phone, text)
    # dev: โชว์ใน terminal
    print(f"\n[SMS -> {phone}] {text}\n")
    return {"ok": True, "provider": "console", "dev": True}


def _send_twilio(phone: str, text: str) -> dict:
    sid    = os.environ.get("TWILIO_ACCOUNT_SID")
    token  = os.environ.get("TWILIO_AUTH_TOKEN")
    sender = os.environ.get("TWILIO_FROM")
    if not (sid and token and sender):
        print("[sms] Twilio env ไม่ครบ — ตั้ง TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM")
        return {"ok": False, "provider": "twilio",
                "error": "Twilio env ไม่ครบ (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM)"}
    to   = "+66" + phone[1:] if phone.startswith("0") else phone
    data = urllib.parse.urlencode({"To": to, "From": sender, "Body": text}).encode()
    url  = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req  = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"ok": resp.status < 300, "provider": "twilio"}
    except Exception as e:
        return {"ok": False, "provider": "twilio", "error": str(e)}


def _send_thaibulksms(phone: str, text: str) -> dict:
    """ThaiBulkSMS — https://www.thaibulksms.com
    Env: THAIBULKSMS_KEY, THAIBULKSMS_SECRET
    """
    key    = os.environ.get("THAIBULKSMS_KEY")
    secret = os.environ.get("THAIBULKSMS_SECRET")
    if not (key and secret):
        return {"ok": False, "provider": "thaibulksms",
                "error": "THAIBULKSMS_KEY / THAIBULKSMS_SECRET ไม่ครบ"}
    to   = "66" + phone[1:] if phone.startswith("0") else phone
    data = urllib.parse.urlencode({
        "username": key, "password": secret,
        "msisdn": to, "message": text, "sender": "SmartHawker",
    }).encode()
    req = urllib.request.Request(
        "https://secure.thaibulksms.com/sms_api.php", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            ok   = "Success" in body or body.strip().startswith("0")
            return {"ok": ok, "provider": "thaibulksms"}
    except Exception as e:
        return {"ok": False, "provider": "thaibulksms", "error": str(e)}


def _send_awssns(phone: str, text: str) -> dict:
    """AWS SNS — https://docs.aws.amazon.com/sns/
    Env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION (default: ap-southeast-1)
    Install: pip install boto3
    """
    try:
        import boto3  # type: ignore
        region = os.environ.get("AWS_REGION", "ap-southeast-1")
        sns    = boto3.client("sns", region_name=region)
        to     = "+66" + phone[1:] if phone.startswith("0") else phone
        sns.publish(
            PhoneNumber=to, Message=text,
            MessageAttributes={"AWS.SNS.SMS.SMSType": {
                "DataType": "String", "StringValue": "Transactional"}})
        return {"ok": True, "provider": "awssns"}
    except ImportError:
        return {"ok": False, "provider": "awssns",
                "error": "boto3 ไม่ได้ติดตั้ง: pip install boto3"}
    except Exception as e:
        return {"ok": False, "provider": "awssns", "error": str(e)}
