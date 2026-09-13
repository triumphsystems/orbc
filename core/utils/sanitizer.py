def sanitize_error_message(error: str | None) -> str | None:
    """Sanitizes internal driver, database, and system exceptions to avoid leaking internal details."""
    if not error:
        return None
    return "An unexpected error occurred while processing the request. Please try again later."
