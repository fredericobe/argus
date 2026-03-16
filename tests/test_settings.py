from app.config.settings import ArgusSettings


def test_csv_domain_parsing() -> None:
    settings = ArgusSettings(
        ARGUS_OPENAI_API_KEY="test",
        ARGUS_ALLOWED_DOMAINS="Amazon.com,WWW.AMAZON.COM",
        ARGUS_BLOCKED_DOMAINS="paypal.com, Bad.com",
    )
    assert settings.allowed_domains == ["amazon.com", "www.amazon.com"]
    assert settings.blocked_domains == ["paypal.com", "bad.com"]
