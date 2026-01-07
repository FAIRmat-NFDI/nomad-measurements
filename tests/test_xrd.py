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


def test_bruker_raw_parser():
    """
    Tests Bruker/Siemens RAW v4 format-specific features.

    This test focuses on RAW-specific parsing that isn't covered by
    test_normalize_all:
    - Scan axis name extraction from binary format
    - Anode material extraction from binary format (offset 0x01A8)
    - Wavelength lookup from anode material reference table

    General features (data arrays, normalization, etc.) are tested in
    test_normalize_all.
    """
    from fairmat_readers_xrd import read_bruker_raw

    raw_file = 'tests/data/xrd/TwoTheta_scan_scrambled.raw'

    # Verify file exists
    assert os.path.exists(raw_file), f'Test file not found: {raw_file}'

    # Read the RAW file
    result = read_bruker_raw(raw_file)

    # TEST RAW-SPECIFIC FEATURES:

    # 1. Scan axis name extraction from binary format (offset 0x04D0)
    assert result['scanmotname'] == 'Theta', (
        f"Expected scanmotname='Theta', got '{result['scanmotname']}'"
    )
    assert result['metadata']['scan_axis'] == 'Theta', (
        f"Expected scan_axis='Theta', got '{result['metadata']['scan_axis']}'"
    )

    # 2. Source metadata extraction
    # (RAW-specific: anode material from binary + wavelength lookup)
    source = result['metadata']['source']

    # Anode material extracted from offset 0x01A8 in binary file
    assert source['anode_material'] == 'Cu'

    # Wavelengths looked up from reference table based on anode material
    # Verify Cu wavelength values from International Tables for Crystallography
    assert source['kAlpha1'] == pytest.approx(1.540598, abs=1e-6)
    assert source['kAlpha2'] == pytest.approx(1.544426, abs=1e-6)
    assert source['kBeta'] == pytest.approx(1.392250, abs=1e-6)
    # K-alpha2/K-alpha1 ratio is always 0.5 for all elements
    expected_ratio = 0.5
    assert source['ratioKAlpha2KAlpha1'] == expected_ratio

    # 3. Sample ID extraction
    assert result['metadata']['sample_id'] == 'HeOx-1001-nsp-sps-900C-10min-01-poliert'
