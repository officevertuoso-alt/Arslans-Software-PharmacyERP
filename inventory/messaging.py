"""
SMS / WhatsApp gateway helpers for Arslan's Software Pharmacy ERP.

Providers (env):
  SMS_PROVIDER / WHATSAPP_PROVIDER: console | http | twilio
  SMS_API_URL, SMS_API_KEY, SMS_SENDER_ID
  WHATSAPP_API_URL, WHATSAPP_API_KEY, WHATSAPP_FROM
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SMS_FROM, TWILIO_WHATSAPP_FROM
  MESSAGING_ENABLED=1 to actually call external APIs

Phone numbers: normalize to digits; prefer 92xxxxxxxxxx for PK.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Optional, Tuple

from django.conf import settings


def normalize_pk_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('0') and len(digits) == 11:
        digits = '92' + digits[1:]
    if len(digits) == 10 and digits.startswith('3'):
        digits = '92' + digits
    return digits


def _http_post(url: str, payload: dict, headers: Optional[dict] = None, auth: Optional[Tuple[str, str]] = None) -> Tuple[bool, str]:
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if auth:
        import base64
        token = base64.b64encode(f'{auth[0]}:{auth[1]}'.encode()).decode()
        req.add_header('Authorization', f'Basic {token}')
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return True, body[:2000]
    except urllib.error.HTTPError as e:
        return False, e.read().decode('utf-8', errors='replace')[:2000]
    except Exception as e:
        return False, str(e)[:500]


def send_sms(to_phone: str, body: str) -> Tuple[str, str, str]:
    """
    Returns (status, provider, response_text)
    status: sent | failed | skipped
    """
    to = normalize_pk_phone(to_phone)
    if len(to) < 10:
        return 'failed', 'none', 'Invalid phone'
    provider = getattr(settings, 'SMS_PROVIDER', 'console')
    enabled = getattr(settings, 'MESSAGING_ENABLED', False)

    if provider == 'console' or not enabled:
        msg = f'[SMS console] to=+{to} body={body[:120]}'
        return ('skipped' if not enabled else 'sent'), 'console', msg

    if provider == 'http':
        url = getattr(settings, 'SMS_API_URL', '')
        if not url:
            return 'failed', 'http', 'SMS_API_URL not set'
        payload = {
            'to': to,
            'message': body,
            'sender': getattr(settings, 'SMS_SENDER_ID', 'ARSALAN'),
            'api_key': getattr(settings, 'SMS_API_KEY', ''),
        }
        ok, resp = _http_post(url, payload, headers={'Authorization': f"Bearer {getattr(settings, 'SMS_API_KEY', '')}"})
        return ('sent' if ok else 'failed'), 'http', resp

    if provider == 'twilio':
        sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        from_n = getattr(settings, 'TWILIO_SMS_FROM', '')
        if not (sid and token and from_n):
            return 'failed', 'twilio', 'Twilio SMS env incomplete'
        url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
        # form-encoded for Twilio
        import urllib.parse
        data = urllib.parse.urlencode({
            'To': f'+{to}',
            'From': from_n,
            'Body': body,
        }).encode()
        req = urllib.request.Request(url, data=data, method='POST')
        import base64
        req.add_header('Authorization', 'Basic ' + base64.b64encode(f'{sid}:{token}'.encode()).decode())
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return 'sent', 'twilio', resp.read().decode()[:2000]
        except Exception as e:
            return 'failed', 'twilio', str(e)[:500]

    return 'failed', provider, 'Unknown SMS provider'


def send_whatsapp(to_phone: str, body: str) -> Tuple[str, str, str]:
    to = normalize_pk_phone(to_phone)
    if len(to) < 10:
        return 'failed', 'none', 'Invalid phone'
    provider = getattr(settings, 'WHATSAPP_PROVIDER', 'console')
    enabled = getattr(settings, 'MESSAGING_ENABLED', False)

    if provider == 'console' or not enabled:
        msg = f'[WhatsApp console] to=+{to} body={body[:120]}'
        return ('skipped' if not enabled else 'sent'), 'console', msg

    if provider == 'http':
        url = getattr(settings, 'WHATSAPP_API_URL', '')
        if not url:
            return 'failed', 'http', 'WHATSAPP_API_URL not set'
        payload = {
            'to': to,
            'message': body,
            'from': getattr(settings, 'WHATSAPP_FROM', ''),
            'api_key': getattr(settings, 'WHATSAPP_API_KEY', ''),
        }
        ok, resp = _http_post(
            url, payload,
            headers={'Authorization': f"Bearer {getattr(settings, 'WHATSAPP_API_KEY', '')}"},
        )
        return ('sent' if ok else 'failed'), 'http', resp

    if provider == 'twilio':
        sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        from_n = getattr(settings, 'TWILIO_WHATSAPP_FROM', '') or getattr(settings, 'WHATSAPP_FROM', '')
        if not (sid and token and from_n):
            return 'failed', 'twilio', 'Twilio WhatsApp env incomplete'
        url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
        import urllib.parse
        data = urllib.parse.urlencode({
            'To': f'whatsapp:+{to}',
            'From': from_n if from_n.startswith('whatsapp:') else f'whatsapp:{from_n}',
            'Body': body,
        }).encode()
        req = urllib.request.Request(url, data=data, method='POST')
        import base64
        req.add_header('Authorization', 'Basic ' + base64.b64encode(f'{sid}:{token}'.encode()).decode())
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return 'sent', 'twilio', resp.read().decode()[:2000]
        except Exception as e:
            return 'failed', 'twilio', str(e)[:500]

    return 'failed', provider, 'Unknown WhatsApp provider'


def dispatch(channel: str, to_phone: str, body: str, *, user=None, purpose: str = '', bill: str = ''):
    """Send and write MessageLog. channel: sms | whatsapp"""
    from inventory.models import MessageLog

    channel = (channel or 'sms').lower()
    if channel == 'whatsapp':
        status, provider, resp = send_whatsapp(to_phone, body)
        ch = MessageLog.CHANNEL_WHATSAPP
    else:
        status, provider, resp = send_sms(to_phone, body)
        ch = MessageLog.CHANNEL_SMS

    log = MessageLog.objects.create(
        channel=ch,
        to_phone=normalize_pk_phone(to_phone),
        body=body,
        status=status,
        provider=provider,
        provider_response=resp or '',
        purpose=purpose[:64],
        related_bill=(bill or '')[:32],
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    return log
