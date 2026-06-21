import os
import json
import logging
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class ZeroTrustMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if settings.MTLS_REQUIRED:
            client_cert = request.META.get('SSL_CLIENT_CERT') or request.META.get('HTTP_X_SSL_CLIENT_CERT')
            if not client_cert:
                logger.warning('ZeroTrust: missing client certificate for request %s', request.path)
                return HttpResponseForbidden('mTLS is required')

            allowed_fps = settings.MTLS_ALLOWED_CLIENT_FINGERPRINTS
            if allowed_fps:
                sig = self._extract_cert_fingerprint(client_cert)
                if sig not in allowed_fps:
                    logger.warning('ZeroTrust: client certificate fingerprint mismatch for request %s', request.path)
                    return HttpResponseForbidden('Invalid client certificate')

    def _extract_cert_fingerprint(self, cert_pem):
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.serialization import Encoding
            from cryptography.hazmat.backends import default_backend
            if isinstance(cert_pem, bytes):
                cert_pem = cert_pem.decode('utf-8')
            cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'), default_backend())
            digest = cert.fingerprint(hashes.SHA256())
            return digest.hex()
        except Exception:
            return ''

class EmergencyLockdownMiddleware(MiddlewareMixin):
    def process_request(self, request):
        lockdown_file = os.getenv('EMERGENCY_LOCKDOWN_FILE', '/tmp/lockdown.flag')
        if os.path.exists(lockdown_file):
            logger.warning('Emergency lockdown active: denying request %s', request.path)
            return HttpResponseForbidden('Emergency lockdown active')

class RequestAuditMiddleware(MiddlewareMixin):
    REDACTED_HEADERS = {
        'HTTP_COOKIE',
        'HTTP_AUTHORIZATION',
        'HTTP_X_CSRFTOKEN',
        'HTTP_X_CSRF_TOKEN',
        'HTTP_PROXY_AUTHORIZATION',
    }

    def _sanitize_headers(self, headers):
        sanitized = {}
        for key, value in headers.items():
            if key in self.REDACTED_HEADERS:
                sanitized[key] = 'REDACTED'
            else:
                sanitized[key] = value
        return sanitized

    def process_request(self, request):
        request.audit_payload = {
            'method': request.method,
            'path': request.path,
            'user': request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous',
            'ip_address': request.META.get('REMOTE_ADDR'),
            'headers': self._sanitize_headers({k: v for k, v in request.META.items() if k.startswith('HTTP_')}),
        }

    def process_response(self, request, response):
        try:
            audit = getattr(request, 'audit_payload', None)
            if audit is not None:
                audit['status_code'] = response.status_code
                audit['content_length'] = response.get('Content-Length', None)
                logger.info('RequestAudit: %s', json.dumps(audit))
        except Exception:
            logger.exception('Failed to log request audit data')
        return response
