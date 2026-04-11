class MymlError(Exception):
    """Base error for caller-facing Myml failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "myml-error",
        category: str = "error",
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.line = line
        self.column = column

    def __str__(self) -> str:
        if self.line is not None and self.column is not None:
            return f"{self.message} (line {self.line}, column {self.column})"
        return self.message


class ParseError(MymlError):
    """Raised when Myml input is invalid."""


class ModeError(MymlError):
    """Raised when a caller supplies an unsupported mode."""
