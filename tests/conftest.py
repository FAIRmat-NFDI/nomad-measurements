import pytest
import structlog
from structlog.testing import LogCapture


@pytest.fixture(
    name='caplog',
    scope='function',
)
def fixture_caplog(request):
    """
    Extracts log messages from the logger and raises an assertion error if the specified
    log levels in the `request.param` are found.
    """
    caplog = LogCapture()
    processors = structlog.get_config()['processors']
    old_processors = processors.copy()

    try:
        processors.clear()
        processors.append(caplog)
        structlog.configure(processors=processors)
        yield caplog
        for record in caplog.entries:
            if record['log_level'] in request.param:
                assert False, record
    finally:
        processors.clear()
        processors.extend(old_processors)
        structlog.configure(processors=processors)
