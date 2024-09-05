import json

import pytest
from nomad.utils import structlogging


@pytest.fixture(scope='function')
def capture_error_from_logger(caplog):
    """
    Extracts log messages from the logger and raises an assertion error if any
    ERROR messages are found.
    """
    caplog.handler.formatter = structlogging.ConsoleFormatter()
    yield caplog
    for record in caplog.get_records(when='call'):
        if record.levelname in ['ERROR']:
            try:
                msg = structlogging.ConsoleFormatter.serialize(json.loads(record.msg))
            except Exception:
                msg = record.msg
            assert False, msg
