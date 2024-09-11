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
    params=[
        '3DM_test01.Probe.Raw.asc',
        'F4-P3HT 1-10 0,5 mgml.Probe.Raw.asc',
        'KTF-D.Probe.Raw.asc',
        'Sample5926.Probe.Raw.asc',
        'sphere_test01.Probe.Raw.asc',
    ]
)
def parsed_archive(request):
    """
    Sets up data for testing and cleans up after the test.
    """
    rel_file = os.path.join(
        os.path.dirname(__file__), '../data/transmission', request.param
    )
    file_archive = parse(rel_file)[0]
    measurement = os.path.join(
        os.path.dirname(__file__),
        '../data/transmission',
        '.'.join(request.param.split('.')[:-1]) + '.archive.json',
    )
    assert file_archive.data.measurement.m_proxy_value == os.path.abspath(measurement)
    measurement_archive = parse(measurement)[0]

    yield measurement_archive

    if os.path.exists(measurement):
        os.remove(measurement)


def test_normalize_all(parsed_archive):
    normalize_all(parsed_archive)
    # TODO test the normalized data
