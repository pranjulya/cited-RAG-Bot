from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-rule failures."""


class InvalidLifecycleTransitionError(DomainError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"invalid document-version transition {current} -> {target}")


class DuplicateIdentityError(DomainError):
    def __init__(self, message: str = "duplicate identifier rejected") -> None:
        super().__init__(message)


class DuplicateContentHashError(DomainError):
    def __init__(self, message: str = "content hash already exists in this collection") -> None:
        super().__init__(message)


class OptimisticConcurrencyError(DomainError):
    def __init__(self, message: str = "lifecycle update did not match expected status") -> None:
        super().__init__(message)


class InvalidPdfError(DomainError):
    def __init__(self, message: str = "file is not an accepted PDF") -> None:
        super().__init__(message)


class EmptyUploadError(DomainError):
    def __init__(self, message: str = "uploaded file is empty") -> None:
        super().__init__(message)


class PayloadTooLargeError(DomainError):
    def __init__(self, message: str = "uploaded file exceeds the configured size limit") -> None:
        super().__init__(message)


class StorageError(DomainError):
    def __init__(self, message: str = "object storage operation failed") -> None:
        super().__init__(message)
