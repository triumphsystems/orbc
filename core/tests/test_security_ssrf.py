from core.utils.security import is_ip_prohibited, validate_url_target


def test_validate_url_target_allows_public_domains():
    safe_urls = [
        "https://www.researchgate.net/publication/12345",
        "https://arxiv.org/html/2601.13243v1",
        "https://github.com/torvalds/linux",
        "https://google.com",
    ]
    for url in safe_urls:
        valid, reason = validate_url_target(url)
        assert valid is True, f"Expected {url} to be allowed, but got blocked: {reason}"


def test_validate_url_target_blocks_restricted_ips_and_metadata():
    blocked_urls = [
        "http://127.0.0.1:8000/admin",
        "http://localhost:8000",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://10.0.0.1/secrets",
        "http://192.168.1.1/router",
    ]
    for url in blocked_urls:
        valid, reason = validate_url_target(url, allow_private=False)
        assert valid is False, f"Expected {url} to be blocked, but it passed!"
        assert reason is not None


def test_is_ip_prohibited():
    assert is_ip_prohibited("127.0.0.1") is True
    assert is_ip_prohibited("169.254.169.254") is True
    assert is_ip_prohibited("10.0.0.1") is True
    assert is_ip_prohibited("192.168.0.1") is True
    assert is_ip_prohibited("8.8.8.8") is False
    assert is_ip_prohibited("1.1.1.1") is False
    # Non-IP string should return False (not a prohibited IP)
    assert is_ip_prohibited("arxiv.org") is False
