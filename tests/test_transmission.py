#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import pytest
from nomad.client import normalize_all

test_files = [
    'tests/data/transmission/3DM_test01.Probe.Raw.asc',
    'tests/data/transmission/F4-P3HT 1-10 0,5 mgml.Probe.Raw.asc',
    'tests/data/transmission/KTF-D.Probe.Raw.asc',
    'tests/data/transmission/Sample5926.Probe.Raw.asc',
    'tests/data/transmission/sphere_test01.Probe.Raw.asc',
]
log_levels = ['error', 'critical']


@pytest.mark.parametrize(
    'parsed_measurement_archive, caplog',
    [(file, log_level) for file in test_files for log_level in log_levels],
    indirect=True,
)
def test_normalize_all(parsed_measurement_archive, caplog):
    """
    Tests the normalization of the parsed archive.

    Args:
        parsed_archive (pytest.fixture): Fixture to handle the parsing of archive.
        caplog (pytest.fixture): Fixture to capture errors from the logger.
    """
    normalize_all(parsed_measurement_archive)
    # TODO test the normalized data
