from app.services.message_privacy import (
    METADATA_ONLY_PLACEHOLDER,
    prepare_message_for_storage,
)


def test_keeps_normal_message_as_full() -> None:
    result = prepare_message_for_storage(
        "Jadwal kelas 7A hari Senin",
        storage_policy="full",
    )

    assert result.content == "Jadwal kelas 7A hari Senin"
    assert result.storage_policy == "full"
    assert result.contains_sensitive_data is False


def test_automatically_redacts_phone_number() -> None:
    result = prepare_message_for_storage(
        "Nomor saya 081234567890",
        storage_policy="full",
    )

    assert result.content == "Nomor saya [PHONE]"
    assert result.storage_policy == "redacted"
    assert result.contains_sensitive_data is True


def test_redacts_email_address() -> None:
    result = prepare_message_for_storage(
        "Email saya siswa@example.com",
        storage_policy="redacted",
    )

    assert result.content == "Email saya [EMAIL]"
    assert result.storage_policy == "redacted"
    assert result.contains_sensitive_data is True


def test_metadata_only_does_not_store_raw_content() -> None:
    result = prepare_message_for_storage(
        "Saya sakit dan perlu surat izin",
        storage_policy="metadata_only",
    )

    assert result.content == METADATA_ONLY_PLACEHOLDER
    assert result.storage_policy == "metadata_only"
    assert result.contains_sensitive_data is True
    assert "sakit" not in result.content