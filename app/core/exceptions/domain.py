from app.core.exceptions.base import AppException


class AuthenticationError(AppException):
    """Raised when authentication fails (wrong password, invalid token, etc.)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthorizationError(AppException):
    """Raised when a user lacks permission for an action."""

    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message)


class ResourceNotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(message)


class DuplicateResourceError(AppException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource: str = "Resource", identifier: str = ""):
        message = f"{resource} already exists"
        if identifier:
            message = f"{resource} '{identifier}' already exists"
        super().__init__(message)


class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message)


class JiraConnectionError(AppException):
    """Raised when connection to Jira API fails."""

    def __init__(self, message: str = "Failed to connect to Jira"):
        super().__init__(message)


class JiraAuthenticationError(AppException):
    """Raised when Jira API authentication fails (invalid token, etc.)."""

    def __init__(self, message: str = "Jira authentication failed - check your API token"):
        super().__init__(message)


class JiraRateLimitError(AppException):
    """Raised when Jira API rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None):
        message = "Jira API rate limit exceeded"
        if retry_after:
            message += f" - retry after {retry_after} seconds"
        self.retry_after = retry_after
        super().__init__(message)


class SessionExpiredError(AppException):
    """Raised when the user's session has expired."""

    def __init__(self, message: str = "Your session has expired - please log in again"):
        super().__init__(message)
