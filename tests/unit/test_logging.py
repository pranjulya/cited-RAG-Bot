from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from cited_rag.config import Settings
from cited_rag.main import _configure_logging
from cited_rag.observability.correlation import CorrelationIdFilter


@pytest.fixture
def isolated_root_logging() -> Iterator[None]:
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_filters = list(root.filters)
    old_level = root.level
    for handler in old_handlers:
        root.removeHandler(handler)
    for log_filter in old_filters:
        root.removeFilter(log_filter)
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for log_filter in list(root.filters):
        root.removeFilter(log_filter)
    for handler in old_handlers:
        root.addHandler(handler)
    for log_filter in old_filters:
        root.addFilter(log_filter)
    root.setLevel(old_level)


def test_child_logger_records_format_with_default_correlation_id(
    isolated_root_logging: None,
) -> None:
    _configure_logging(Settings(_env_file=None, log_level="INFO"))
    root = logging.getLogger()
    assert root.handlers, "expected basicConfig to attach a handler"
    handler = root.handlers[0]
    assert any(isinstance(item, CorrelationIdFilter) for item in handler.filters)
    handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s correlation_id=%(correlation_id)s %(message)s")
    )

    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Application startup complete.",
        args=(),
        exc_info=None,
    )
    assert handler.filter(record)
    formatted = handler.format(record)
    assert "correlation_id=-" in formatted
    assert "Application startup complete." in formatted
