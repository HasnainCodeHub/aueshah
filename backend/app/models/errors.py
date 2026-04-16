"""Custom exception classes for the application."""


class ChatException(Exception):
    """Base exception for chat-related errors."""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationError(ChatException):
    """Request validation failed."""
    def __init__(self, message: str):
        super().__init__(message, code=400)


class InjectionDetected(ChatException):
    """Prompt injection attempt detected."""
    def __init__(self, message: str = "Invalid input detected"):
        super().__init__(message, code=400)


class OffTopic(ChatException):
    """Client asked something outside Aueshah's concierge scope."""
    def __init__(self, message: str = "Out of scope"):
        super().__init__(message, code=200)


class RAGUnavailable(ChatException):
    """Vector store/RAG service is unavailable."""
    def __init__(self, message: str = "RAG service unavailable"):
        super().__init__(message, code=503)


class AITimeout(ChatException):
    """AI provider request timed out."""
    def __init__(self, message: str = "AI service timeout"):
        super().__init__(message, code=503)


class AIError(ChatException):
    """AI provider returned an error."""
    def __init__(self, message: str):
        super().__init__(message, code=503)


class ToolError(ChatException):
    """Tool execution failed."""
    def __init__(self, message: str):
        super().__init__(message, code=500)


class InternalError(ChatException):
    """Unexpected internal error."""
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, code=500)


class AuthFailure(ChatException):
    """Authentication or authorization failed."""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code=401)


class RateLimited(ChatException):
    """Too many requests from this client."""
    def __init__(self, message: str = "Too many requests. Please wait a moment."):
        super().__init__(message, code=429)


class CooldownActive(ChatException):
    """User is within the Noor cooldown period."""
    def __init__(self, message: str = "You have an active Noor request. New requests unlock after the cooldown period."):
        super().__init__(message, code=409)


class NoorPendingConflict(ChatException):
    """User already has a pending Noor request."""
    def __init__(self, message: str = "You already have a pending Noor request under review."):
        super().__init__(message, code=409)


class DatabaseUnavailable(ChatException):
    """Database connection failed."""
    def __init__(self, message: str = "Database temporarily unavailable"):
        super().__init__(message, code=503)
