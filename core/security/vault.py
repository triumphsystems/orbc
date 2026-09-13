import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

from core.config.settings import get_settings

logger = logging.getLogger("core.security.vault")


class SecretVault:
    """Enterprise secret encryption, decryption, and masking utility."""

    _cipher: Fernet | None = None

    @classmethod
    def _get_cipher(cls) -> Fernet:
        if cls._cipher is None:
            settings = get_settings()
            raw_key = os.getenv("ORBIT_SECRET_KEY") or settings.orbit_secret_key
            if not raw_key:
                raise ValueError("ORBIT_SECRET_KEY must be configured in settings or environment.")
            derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode()).digest())
            cls._cipher = Fernet(derived_key)
        return cls._cipher

    MASK_BULLET: str = "•"
    MASK_PLACEHOLDER: str = "••••"

    @classmethod
    def is_masked(cls, secret: str | None) -> bool:
        """Checks if a secret contains masked placeholder bullets or is empty."""
        return not secret or cls.MASK_PLACEHOLDER in str(secret)

    @classmethod
    def mask_secret(cls, secret: str | None) -> str:
        """Masks sensitive credentials e.g. '••••••••3f8a'."""
        if not secret:
            return ""
        if len(secret) <= 6:
            return cls.MASK_PLACEHOLDER + cls.MASK_PLACEHOLDER
        return f"{cls.MASK_PLACEHOLDER}{cls.MASK_PLACEHOLDER}{secret[-4:]}"

    @classmethod
    def encrypt_secret(cls, plain_text: str | None) -> str:
        """Encrypts a sensitive secret string into an AES-128-CBC + HMAC ciphertext."""
        if not plain_text:
            return ""
        try:
            cipher = cls._get_cipher()
            return cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error(f"Secret encryption failed: {e}")
            raise RuntimeError(f"Failed to encrypt sensitive secret: {e}") from e

    @classmethod
    def decrypt_secret(cls, cipher_text: str | None) -> str:
        """Decrypts a ciphertext string back to plain text."""
        if not cipher_text:
            return ""
        try:
            cipher = cls._get_cipher()
            return cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Fallback for unencrypted legacy secrets
            return cipher_text
        except Exception as e:
            logger.warning(f"Secret decryption failed: {e}")
            return cipher_text
