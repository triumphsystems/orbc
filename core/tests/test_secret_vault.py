import pytest
from core.security.vault import SecretVault


@pytest.fixture(autouse=True)
def setup_vault_key(monkeypatch):
    monkeypatch.setenv("ORBIT_SECRET_KEY", "test-secret-key-for-vault-encryption-32bytes")
    SecretVault._cipher = None
    yield
    SecretVault._cipher = None


def test_secret_masking():
    assert SecretVault.mask_secret("") == ""
    assert SecretVault.mask_secret(None) == ""
    assert SecretVault.mask_secret("short") == "••••••••"
    assert SecretVault.mask_secret("sk-live-abcdef123456") == "••••••••3456"
    assert SecretVault.mask_secret("https://hooks.slack.com/services/T00/B00/X12345678") == "••••••••5678"

    assert SecretVault.is_masked("") is True
    assert SecretVault.is_masked(None) is True
    assert SecretVault.is_masked("••••••••3456") is True
    assert SecretVault.is_masked("\u2022\u2022\u2022\u2022") is True
    assert SecretVault.is_masked("sk-live-real-secret-key-1234") is False



def test_secret_encryption_and_decryption():
    raw_secret = "my-secret-aws-token-998877"
    encrypted = SecretVault.encrypt_secret(raw_secret)
    assert encrypted != raw_secret
    assert len(encrypted) > len(raw_secret)

    decrypted = SecretVault.decrypt_secret(encrypted)
    assert decrypted == raw_secret


def test_secret_vault_handles_empty():
    assert SecretVault.encrypt_secret("") == ""
    assert SecretVault.decrypt_secret("") == ""
    assert SecretVault.encrypt_secret(None) == ""
