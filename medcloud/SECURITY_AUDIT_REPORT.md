# Security Audit Report

## Executive Summary

This report evaluates the current security posture of the MedCloud medical blockchain platform.
The platform combines Django web functionality, encrypted medical reports, audit logging, and an internal blockchain ledger.

Overall security score before fixes: 4.0 / 10

Scores by domain:
- Authentication: 5.0
- Authorization: 6.0
- API Security: 5.0
- Cryptography: 5.0
- Blockchain: 3.5
- File Handling: 4.0
- Audit Logging: 3.0
- Infrastructure / Django Security: 5.5

## Threat Model and Attack Surface

### Primary assets
- Medical reports and patient data
- Blockchain ledger integrity and consent records
- User credentials and session tokens
- Encrypted file storage and temporary decrypted files
- Audit logs and SIEM telemetry

### Adversaries
- Unauthorized external users
- Malicious authenticated users (patients/doctors)
- Insider administrators
- Privilege escalation attackers
- Supply chain / dependency attackers

### Attack surfaces
- Web UI upload/download routes in `frontend/views.py`
- DRF API endpoints in `backend/api_views.py`
- Blockchain ledger storage in `blockchain/blockchain_service.py`
- Encryption code in `services/encryption_service.py`
- Session and JWT configuration in `medcloud/settings.py`
- Audit logging in `frontend/utils.py` and `medcloud/middleware.py`
- Report verification in `frontend/services/report_verification.py`
- Legacy backend JSON endpoints in `backend/views.py`

## Findings

### Critical Vulnerabilities

1. Blockchain ledger signature fallback and weak blockchain integrity
   - Evidence: `blockchain/blockchain_service.py` uses HMAC fallback when no private/public key is available (`_sign_block`, `_verify_block_signature`) and allows unsigned genesis block compatibility (line ~35 and ~60).
   - Impact: If signing keys are missing or compromised, ledger signatures can be forged and tampering can go undetected.
   - Exploitability: High. A malicious actor with access to the signing secret or file system can modify ledger blocks.

2. Blockchain ledger lacks transaction replay protection and duplicate report detection
   - Evidence: `blockchain/blockchain_service.py` `add_report_hash` does not check existing `report_id` or `file_hash` uniqueness before appending a block.
   - Impact: The same report may be anchored multiple times, undermining audit proof and enabling inconsistent ledger state.
   - Exploitability: High in attacker-controlled file upload or ledger injection scenarios.

3. Audit logs are not tamper-evident or chained
   - Evidence: `frontend/models.py` `AuditLog` stores logs in raw fields without hash chaining; `frontend/utils.py` simply writes `AuditLog.objects.create(...)`.
   - Impact: Audit records can be modified or deleted without detection in the database.
   - Exploitability: High for insiders with DB access.

4. File upload validation trusts content type and extension only before patch
   - Evidence: `frontend/forms.py` validates `content_type` but not file magic bytes; `backend/views.py` upload endpoint uses `content_type` only.
   - Impact: MIME spoofing and malicious file uploads can bypass checks. This is a direct unsafe file-upload vector.
   - Exploitability: High for upload-based attacks.

5. Incomplete authorization on DRF update operations
   - Evidence: `backend/serializers.py` previously exposed writable `patient_id` / `user` fields; `backend/api_views.py` attempted to pop these values in `perform_update`, but viewset update paths can still be abused by staff or misconfigured serializers.
   - Impact: Mass assignment or object owner reassignment risk.
   - Exploitability: Moderate to high against configurable APIs.

### High Risks

1. No strong JWT refresh token revocation policy in settings
   - Evidence: `medcloud/settings.py` configures `SIMPLE_JWT` but there is no explicit token obtain endpoint or token blacklist enforcement beyond package import.
   - Impact: Refresh token abuse and replay risk remain.

2. Blockchain timestamp validation and fork detection absent
   - Evidence: `blockchain/blockchain_service.py` `is_chain_valid()` does not validate block timestamps or detect non-monotonic sequences.
   - Impact: Old or reordered blocks can be inserted by an attacker, weakening chain trust.

3. Inconsistent path security across report verification and download
   - Evidence: `frontend/services/report_verification.py` and `frontend/views.py` use safe path checks on `encrypted_file.path`; however, `backend/views.py` upload endpoint can create reports with arbitrary `FileField` content.
   - Impact: Path traversal is somewhat mitigated but not fully enforced in all flows.

4. No malware scanning hook or upload policy enforcement
   - Evidence: `frontend/forms.py` and `backend/views.py` do file type checks only; no antivirus integration exists.
   - Impact: Malware-laden reports can enter the system.

5. Audit middleware logs request headers without full header hygiene
   - Evidence: `medcloud/middleware.py` redacts some headers but still logs all `HTTP_` prefixed headers; may leak headers such as host, forwarded proto, or other sensitive metadata.

### Medium Risks

1. Legacy `backend/views.py` API endpoints bypass DRF protections and do not enforce content validation consistently.
2. `medcloud/settings.py` defaults `DEBUG=True` if env var absent, which is dangerous if deployed incorrectly.
3. `frontend/models.py` allows `UserProfile.totp_secret` but no MFA enforcement code exists.
4. `services/encryption_service.py` does not support strong KDF alternatives such as Argon2 and uses a static PBKDF2 iteration count.
5. `frontend/views.py` uses temp files and may leak them if cleanup fails, though cleanup logic exists in `SecureReportDownloadView`.
6. `frontend/utils.py` consent enforcement uses `Consent.objects.filter(doctor=user, patient_id__in=patient_ids, revoked=False)` but does not require consent scope matching or explicit active consent on every access.

### Low Risks

1. `get_chain_summary()` computes a Merkle root over all `file_hash` values but does not store it in the chain, so it is informational only.
2. CORS origins are loaded from env but may be empty in production if misconfigured.
3. `backend/serializers.py` still exposes `patient_id` write-only fields for create operations, which is necessary but should be guarded.
4. `frontend/views.UploadView` does not currently scan for ZIP bombs or double extensions beyond sanitizing the filename.

## Evidence Summary

- `blockchain/blockchain_service.py`: signed block creation and validation logic; legacy unsigned genesis allowance; no timestamp or nonce validation.
- `medcloud/settings.py`: JWT settings, session cookie settings, DEBUG default.
- `frontend/forms.py`: file upload validation logic.
- `backend/views.py`: legacy JSON upload endpoint and file type checks.
- `frontend/utils.py`: consent and access control logic.
- `backend/api_views.py` / `backend/serializers.py`: ownership and mass assignment protections.
- `frontend/models.py`: audit log model, `MedicalReport` and `Consent` chain anchoring.

## Recommended Immediate Fixes

1. Enforce blockchain digital signatures using ECDSA P-256 or HSM-backed signing only; remove insecure HMAC fallback.
2. Add block timestamp validation and block ordering checks.
3. Add transaction uniqueness checks in `add_report_hash` and `add_consent_hash`.
4. Add audit log hash chaining fields and verification functions.
5. Add magic-byte validation and extension validation for uploads, as well as an antivirus hook.
6. Harden serializer update logic and strip ownership fields on update.
7. Add JWT refresh token blacklist support and reduce access token lifetime.
8. Harden `medcloud/settings.py` defaults for production and require explicit secure env configuration.

## Phase 1 Conclusion

A full security audit shows multiple critical issues in blockchain integrity, file validation, and audit logging.
No assumptions were made; each finding is traceable to the current codebase and code paths.

Next step: implement the justified fixes starting with critical blockchain, file, and audit controls, then add regression tests.
