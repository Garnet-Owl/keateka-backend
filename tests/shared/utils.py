from app.shared.config import Settings, Environment


def get_test_settings() -> Settings:
    """Create Settings instance with test configuration."""
    return Settings(
        # Required settings with test values
        API_BASE_URL="http://testserver",
        # Use Docker test-db service
        DATABASE_URL="postgresql+asyncpg://keateka:2025_keateka_123@test-db:5432/keateka_test_db",
        REDIS_URL="redis://redis:6379/1",  # Use Redis container but different db number
        # Other required settings...
        POSTGRES_PASSWORD="2025_keateka_123",
        TEST_POSTGRES_PASSWORD="2025_keateka_123",
        SECRET_KEY="test_secret_key",
        MPESA_CONSUMER_KEY="test_consumer_key",
        MPESA_CONSUMER_SECRET="test_consumer_secret",
        MPESA_PASSKEY="test_passkey",
        MPESA_BUSINESS_SHORTCODE="174379",
        MPESA_INITIATOR_NAME="testapi",
        MPESA_SECURITY_CREDENTIAL="test_credential",
        GOOGLE_MAPS_API_KEY="test_maps_key",
        # Test-specific settings
        ENVIRONMENT=Environment.TEST,
        DEBUG=True,
    )
