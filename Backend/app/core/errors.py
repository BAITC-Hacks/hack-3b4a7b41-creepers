from pydantic import BaseModel


class ErrorInfo(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorInfo


class AppError(Exception):
    """Only fixed, public-safe messages belong in this exception."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def info(self) -> ErrorInfo:
        return ErrorInfo(code=self.code, message=self.message)
