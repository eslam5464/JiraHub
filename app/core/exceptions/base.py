class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str = "An application error occurred"):
        self.message = message
        super().__init__(self.message)
