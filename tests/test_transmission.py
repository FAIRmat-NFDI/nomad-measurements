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
    'tests/data/transmission/KTF-D.Probe.Raw.asc',
    'tests/data/transmission/3DM_test01.Probe.Raw.asc',
    'tests/data/transmission/F4-P3HT 1-10 0,5 mgml.Probe.Raw.asc',
    'tests/data/transmission/Sample5926.Probe.Raw.asc',
    'tests/data/transmission/sphere_test01.Probe.Raw.asc',
]
log_levels = ['error', 'critical']
clean_up_extensions = ['.archive.json']


@pytest.mark.parametrize(
    'parsed_measurement_archive, caplog',
    [
        ((file, clean_up_extensions), log_level)
        for file in test_files
        for log_level in log_levels
    ],
    indirect=True,
)
def test_normalize_all(parsed_measurement_archive, caplog):
    """
    Tests the normalization of the parsed archive.

    Args:
        parsed_measurement_archive (pytest.fixture): Fixture to setup the archive.
        caplog (pytest.fixture): Fixture to capture errors from the logger.
    """
    normalize_all(parsed_measurement_archive)


@pytest.mark.parametrize(
    'parsed_measurement_archive, caplog',
    [((test_files[0], clean_up_extensions), log_level) for log_level in log_levels],
    indirect=True,
)
def test_normalized_data(parsed_measurement_archive, caplog):
    """
    Tests the normalized data for a single file.

    Args:
        parsed_measurement_archive (pytest.fixture): Fixture to setup the archive.
        caplog (pytest.fixture): Fixture to capture errors from the logger.
    """
    normalize_all(parsed_measurement_archive)

    # testing normalized data for a single file
    if parsed_measurement_archive.data.data_file == 'KTF-D.Probe.Raw.asc':
        assert (
            parsed_measurement_archive.data.transmission_settings.sample_beam_position
            == 'Front'
        )
        assert parsed_measurement_archive.data.results[0].wavelength.shape == (1001,)
        assert parsed_measurement_archive.data.results[0].transmittance.shape == (1001,)
        assert (
            'UV-Vis-NIR Transmission Spectrophotometry'
            in parsed_measurement_archive.results.eln.methods
        )
