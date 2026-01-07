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
from nomad.client import normalize_all
from nomad.config import config

from nomad_measurements.xrd.schema import XRDResult1D, XRDResult1DHDF5

try:
    import pynxtools  # noqa F401

    HAS_PYNXTOOLS = True
except ImportError:
    HAS_PYNXTOOLS = False

test_files = [
    'tests/data/xrd/XRD-918-16_10.xrdml',
    'tests/data/xrd/m54313_om2th_10.xrdml',
    'tests/data/xrd/m82762_rc1mm_1_16dg_src_slit_phi-101_3dg_-420_mesh_long.xrdml',
    'tests/data/xrd/23-012-AG_2thomegascan_long.brml',
    'tests/data/xrd/EJZ060_13_004_RSM.brml',
    'tests/data/xrd/Omega-2Theta_scan_high_temperature.rasx',
    'tests/data/xrd/RSM_111_sdd=350.rasx',
    'tests/data/xrd/TwoTheta_scan_powder.rasx',
    'tests/data/xrd/TwoTheta_scan_scrambled.raw',  # Bruker RAW v4 (scrambled data)
]
log_levels = ['error', 'critical']
clean_up_extensions = ['.archive.json', '.nxs', '.h5']

# Invalid files for testing negative matching (reject non-matching formats)
invalid_test_files = [
    {
        'filename': 'invalid.raw',
        'content': b'RIGAKU_RAW_FORMAT\x00\x00\x00' + b'\x00' * 1000,
        'description': 'Non-Bruker RAW file (missing RAW4.00 header)',
    },
    # Future: Add other invalid formats here (e.g., fake .xrdml, .brml, etc.)
]


@pytest.mark.parametrize(
    'parsed_measurement_archive, caplog',
    [((file, clean_up_extensions), log_levels) for file in test_files],
    indirect=True,
    ids=[os.path.basename(file) for file in test_files],
)
def test_normalize_all(parsed_measurement_archive, caplog):
    """
    Tests the normalization of the parsed archive.

    Args:
        parsed_archive (pytest.fixture): Fixture to handle the parsing of archive.
        caplog (pytest.fixture): Fixture to capture errors from the logger.
    """
    normalize_all(parsed_measurement_archive)

    # Check XRD settings if available
    if parsed_measurement_archive.data.xrd_settings is not None:
        assert (
            parsed_measurement_archive.data.xrd_settings.source.xray_tube_material
            == 'Cu'
        )
    if (
        parsed_measurement_archive.data.results
        and parsed_measurement_archive.data.results[0].source_peak_wavelength
    ):
        assert parsed_measurement_archive.data.results[
            0
        ].source_peak_wavelength.magnitude == pytest.approx(1.540598, 1e-2)
    if parsed_measurement_archive.data.results and isinstance(
        parsed_measurement_archive.data.results[0], XRDResult1D | XRDResult1DHDF5
    ):
        assert (
            parsed_measurement_archive.results.properties.structural.diffraction_pattern[
                0
            ].incident_beam_wavelength.magnitude
            * 1e10
            == pytest.approx(1.540598, 1e-2)
        )


test_files = [
    'tests/data/xrd/XRD-918-16_10.xrdml',
    'tests/data/xrd/RSM_111_sdd=350.rasx',
]


@pytest.mark.skipif(not HAS_PYNXTOOLS, reason='pynxtools is not installed')
@pytest.mark.parametrize(
    'parsed_measurement_archive, caplog',
    [((file, clean_up_extensions), log_levels) for file in test_files],
    indirect=True,
    ids=[os.path.basename(file) for file in test_files],
)
def test_nexus_results_section(parsed_measurement_archive, caplog):
    """
    Tests the creation of nexus file and the results section.

    Args:
        parsed_archive (pytest.fixture): Fixture to handle the parsing of archive.
        caplog (pytest.fixture): Fixture to capture errors from the logger.
    """
    config.get_plugin_entry_point(
        'nomad_measurements.xrd:schema_entry_point'
    ).use_hdf5_results = True
    normalize_all(parsed_measurement_archive)

    assert parsed_measurement_archive.data.auxiliary_file.endswith('.nxs')
    assert (
        parsed_measurement_archive.data.results[0].intensity.rsplit('#')[-1]
        == '/entry/experiment_result/intensity'
    )


@pytest.mark.parametrize(
    'invalid_file',
    invalid_test_files,
    ids=[f['description'] for f in invalid_test_files],
)
def test_reject_invalid_file_formats(invalid_file, tmp_path):
    """
    Tests that files with invalid headers/formats are not matched by the parser.

    This ensures the parser correctly rejects files that have the right extension
    but wrong format (e.g., non-Bruker .raw files, malformed XML files, etc.).
    Uses NOMAD's natural matching system to verify rejection.

    To add new negative test cases, add entries to the invalid_test_files list
    with 'filename', 'content', and 'description' fields.
    """
    from nomad.client import parse

    # Create the fake file
    fake_file = tmp_path / invalid_file['filename']
    fake_file.write_bytes(invalid_file['content'])

    # Try to parse - should raise AssertionError when no parser matches
    with pytest.raises(AssertionError, match='there is no parser matching'):
        parse(str(fake_file))
