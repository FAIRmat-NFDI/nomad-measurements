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
import os

import pytest
from nomad.client import normalize_all, parse


@pytest.fixture(
    name='parsed_archive',
    params=[
        'ETO_Ch1_TMR_Ch2_Hall.dat',
        #  'ETO_Ch1_TMR_Ch2_Hall.seq',
    ],
)
def fixture_parsed_archive(request):
    """
    Sets up data for testing and cleans up after the test.
    """
    rel_file = os.path.join('tests', 'data', 'ppms', request.param)
    file_archive = parse(rel_file)[0]
    if request.param.endswith('.dat'):
        measurement = os.path.join(
            'tests',
            'data',
            'ppms',
            '.'.join(request.param.split('.')[:-1]) + '.archive.json',
        )
        assert file_archive.data.measurement.m_proxy_value == os.path.abspath(
            measurement
        )
    elif request.param.endswith('.seq'):
        measurement = os.path.join(
            'tests',
            'data',
            'ppms',
            '.'.join(request.param.split('.')[:-1]) + '.seq',
        )
        assert file_archive.data.file_path == os.path.abspath(measurement)
    measurement_archive = parse(measurement)[0]

    yield measurement_archive

    if request.param.endswith('.dat'):
        if os.path.exists(measurement):
            os.remove(measurement)
        additional_files = [
            'ETO_Ch1_TMR_Ch2_Hall_field_sweep_2.0_K.dat',
            'ETO_Ch1_TMR_Ch2_Hall_field_sweep_2.5_K.dat',
            'ETO_Ch1_TMR_Ch2_Hall_field_sweep_3.0_K.dat',
            'ETO_Ch1_TMR_Ch2_Hall_field_sweep_3.5_K.dat',
            'ETO_Ch1_TMR_Ch2_Hall_field_sweep_4.0_K.dat',
        ]
        for filename in additional_files:
            if os.path.exists(os.path.join('tests', 'data', 'ppms', filename)):
                os.remove(os.path.join('tests', 'data', 'ppms', filename))


@pytest.mark.parametrize(
    'caplog',
    ['error', 'critical'],
    indirect=True,
)
def test_normalize_all(parsed_archive, caplog):
    """
    Tests the normalization of the parsed archive.

    Args:
        parsed_archive (pytest.fixture): Fixture to handle the parsing of archive.
        caplog (pytest.fixture): Fixture to capture errors from the logger.
    """
    normalize_all(parsed_archive)

    assert (
        parsed_archive.data.software
        == 'Electrical Transport Option, Release 1.2.0 Build 0'
    )
    #  assert len(parsed_archive.data.steps) == 70 #Noqa: PLR2004
    assert len(parsed_archive.data.data) == 5  # Noqa: PLR2004
    assert len(parsed_archive.data.data[4].time_stamp) == 3623  # Noqa: PLR2004
    assert len(parsed_archive.data.figures) == 5  # Noqa: PLR2004
