"""
Error handling utilities for FastAPI endpoints
Centralizes error handling logic to reduce code duplication
"""
from fastapi import HTTPException
import concurrent.futures


def handle_api_error(
    error: Exception,
    timeout_message: str = "Request timed out",
    error_code: int = 500
) -> None:
    """
    Handle API errors with appropriate HTTP status codes

    Args:
        error: The exception that was raised
        timeout_message: Custom message for timeout errors
        error_code: HTTP status code for generic errors (default: 500)

    Raises:
        HTTPException: With appropriate status code and detail message
    """
    if isinstance(error, concurrent.futures.TimeoutError):
        raise HTTPException(status_code=504, detail=timeout_message)

    # Already an HTTPException, re-raise it
    if isinstance(error, HTTPException):
        raise error

    # Generic error
    raise HTTPException(status_code=error_code, detail=str(error))
