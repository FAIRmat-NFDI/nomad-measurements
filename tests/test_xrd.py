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
    # 'tests/data/xrd/test_sample.raw',  # Tested separately (limited metadata)
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
    # (some formats like .raw don't include source metadata)
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
    if isinstance(
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
    Tests the Bruker/Siemens RAW v4 parser directly.

    Bruker RAW v4 files contain:
    - Scan data (angles, intensities, scan axis)
    - X-ray tube anode material (from which wavelengths are looked up)

    This test validates that the parser correctly extracts all available data.

    Tests:
    - File reading and parsing
    - Scan parameter extraction (start_angle, step_size, num_points, scan_axis)
    - Intensity data extraction
    - Source metadata (anode material, wavelengths)
    - Data array length consistency
    - Value ranges are reasonable for XRD
    """
    from fairmat_readers_xrd import read_bruker_raw

    raw_file = 'tests/data/xrd/test_sample.raw'

    # Verify file exists
    assert os.path.exists(raw_file), f'Test file not found: {raw_file}'

    # Read the RAW file
    result = read_bruker_raw(raw_file)

    # Verify basic structure
    assert result is not None, 'Parser should return data'
    assert isinstance(result, dict), 'Result should be a dictionary'

    # Check for required keys
    assert '2Theta' in result, 'Result should contain 2Theta data'
    assert 'intensity' in result, 'Result should contain intensity data'
    assert 'metadata' in result, 'Result should contain metadata'
    assert 'scanmotname' in result, 'Result should contain scanmotname'

    # Verify scanmotname (scan axis) was extracted
    assert (
        result['scanmotname'] == 'Theta'
    ), f"Expected scanmotname='Theta', got '{result['scanmotname']}'"

    # Verify metadata contains scan_axis
    assert 'scan_axis' in result['metadata'], 'Metadata should contain scan_axis'
    assert (
        result['metadata']['scan_axis'] == 'Theta'
    ), f"Expected scan_axis='Theta', got '{result['metadata']['scan_axis']}'"

    # Check that data arrays exist and have content
    two_theta = result['2Theta']
    intensity = result['intensity']

    assert hasattr(two_theta, 'magnitude'), '2Theta should be a pint Quantity'
    assert hasattr(intensity, 'magnitude'), 'intensity should be a pint Quantity'

    two_theta_values = two_theta.magnitude
    intensity_values = intensity.magnitude

    assert len(two_theta_values) > 0, '2Theta should contain data points'
    assert len(intensity_values) > 0, 'Intensity should contain data points'

    # Verify arrays have matching lengths
    assert len(two_theta_values) == len(
        intensity_values
    ), '2Theta and intensity arrays should have the same length'

    # Verify angle values are in reasonable range for XRD
    max_xrd_angle = 180
    assert min(two_theta_values) >= 0, '2Theta values should be non-negative'
    assert (
        max(two_theta_values) <= max_xrd_angle
    ), f'2Theta values should be <= {max_xrd_angle} degrees'

    # Verify we got the expected number of points from the test file
    # (known from format analysis: test_sample.raw has 7134 points)
    expected_points = 7134
    assert (
        len(two_theta_values) == expected_points
    ), f'Expected {expected_points} data points, got {len(two_theta_values)}'

    # Verify scan parameters are in metadata
    assert 'scan_type' in result['metadata'], 'Metadata should contain scan_type'
    # For single-axis powder diffraction scans
    assert (
        result['metadata']['scan_type'] == 'line'
    ), f"Expected scan_type='line', got '{result['metadata']['scan_type']}'"

    # NEW: Verify source metadata (anode material and wavelengths)
    assert 'source' in result['metadata'], 'Metadata should contain source information'
    source = result['metadata']['source']
    assert isinstance(source, dict), 'Source should be a dictionary'

    # Check anode material was extracted
    assert 'anode_material' in source, 'Source should contain anode_material'
    assert source['anode_material'] == 'Cu', 'Expected Cu anode for test file'

    # Check wavelengths were looked up from anode material (schema uses kAlpha1, kAlpha2, kBeta)
    assert 'kAlpha1' in source, 'Source should contain K-alpha1 wavelength'
    assert 'kAlpha2' in source, 'Source should contain K-alpha2 wavelength'
    assert 'kBeta' in source, 'Source should contain K-beta wavelength'

    # Verify wavelength values are reasonable for Cu
    cu_kalpha1_min = 1.54
    cu_kalpha1_max = 1.55
    cu_kbeta_min = 1.39
    cu_kbeta_max = 1.40
    assert (
        cu_kalpha1_min < source['kAlpha1'] < cu_kalpha1_max
    ), 'Cu K-alpha1 should be ~1.54 Å'
    assert (
        cu_kalpha1_min < source['kAlpha2'] < cu_kalpha1_max
    ), 'Cu K-alpha2 should be ~1.54 Å'
    assert cu_kbeta_min < source['kBeta'] < cu_kbeta_max, 'Cu K-beta should be ~1.39 Å'

    # Note: Count time is still not available in RAW format
    # This would need to be provided via ELN or instrument configuration
