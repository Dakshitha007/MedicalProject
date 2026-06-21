import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from django.conf import settings

logger = logging.getLogger(__name__)


def send_audit_event(payload):
    if not settings.SIEM_INGEST_URL or not settings.SIEM_API_TOKEN:
        logger.debug('SIEM ingest disabled or not configured')
        return

    try:
        body = json.dumps(payload).encode('utf-8')
        request = Request(
            settings.SIEM_INGEST_URL,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {settings.SIEM_API_TOKEN}',
            },
            method='POST',
        )
        with urlopen(request, timeout=10) as response:
            logger.debug('SIEM event sent, status=%s', response.status)
    except HTTPError as exc:
        logger.warning('SIEM event HTTP error: %s', exc)
    except URLError as exc:
        logger.warning('SIEM event network error: %s', exc)
    except Exception as exc:
        logger.exception('SIEM event failed: %s', exc)
