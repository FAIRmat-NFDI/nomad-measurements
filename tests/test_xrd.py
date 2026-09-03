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
from datetime import datetime, timezone

import pytest
import structlog
from nomad.client import normalize_all
from nomad.config import config
from nomad.datamodel import User
from nomad.datamodel.context import ServerContext
from nomad.datamodel.datamodel import EntryArchive, EntryMetadata

from nomad_measurements.xrd.parser import XRDParser
from nomad_measurements.xrd.schema import (
    ELNXRayDiffraction,
    XRDResult1D,
    XRDResult1DHDF5,
)

try:
    import pynxtools  # noqa F401

    HAS_PYNXTOOLS = True
except ImportError:
    HAS_PYNXTOOLS = False

test_files = [
    'tests/data/xrd/XRD-918-16_10.xrdml',
    'tests/data/xrd/m54313_om2th_10.xrdml',
    'tests/data/xrd/m82762_rc1mm_1_16dg_src_slit_phi-101_3dg_-420_mesh_long.xrdml',
    'tests/data/xrd/10_m84325_C_XRR_fast_processed.xrdml',
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
    'data_file_path, expected_archive_file_path',
    [
        ('sample.v1.xrdml', 'samplev1.archive.json'),
        ('folder/sample.v1.xrdml', 'folder/samplev1.archive.json'),
        ('folder.v1/sample.xrdml', 'folder.v1/sample.archive.json'),
        ('folder.v1/sample.v2.xrdml', 'folder.v1/samplev2.archive.json'),
    ],
)
def test_archive_file_path(data_file_path, expected_archive_file_path, monkeypatch):
    archive_file_paths = []

    def mock_create_archive(entry, archive, archive_file_path):
        archive_file_paths.append(archive_file_path)

    monkeypatch.setattr(
        'nomad_measurements.xrd.parser.create_archive', mock_create_archive
    )
    archive = EntryArchive(m_context=ServerContext(), metadata=EntryMetadata())

    XRDParser().parse(f'/tmp/raw/{data_file_path}', archive)

    assert archive_file_paths == [expected_archive_file_path]


@pytest.mark.parametrize(
    'start_time_input, expected_datetime',
    [
        (
            datetime(2020, 8, 4, 19, 53, 22, tzinfo=timezone.utc),
            datetime(2020, 8, 4, 19, 53, 22, tzinfo=timezone.utc),
        ),
        (
            '2020-08-04T19:53:22+02:00',
            datetime.fromisoformat('2020-08-04T19:53:22+02:00'),
        ),
        ('not-a-valid-datetime', None),
        (None, None),
    ],
    ids=['datetime-object', 'iso-string', 'invalid-string', 'missing'],
)
def test_write_xrd_data_links_instrument_and_datetime(
    monkeypatch, start_time_input, expected_datetime
):
    """
    Tests that `write_xrd_data` populates `instruments` and `datetime` from the
    `instrument_id` and `start_time` keys of the reader's metadata dict, mirroring
    the existing `sample_id` -> `samples` behavior. `instruments` is only populated
    under a `ServerContext`. `start_time` is validated with the `datetime` library
    before being used; an incompatible value is dropped rather than raising.
    """

    # `InstrumentReference.normalize` (like `CompositeSystemReference.normalize`)
    # looks up a matching entry via `nomad.search.search`, which requires `fastapi`
    # (only pulled in by nomad-lab's optional `infrastructure` extra, not installed
    # in this project's test environment). `lab_id` is set directly by
    # `write_xrd_data` regardless of what `normalize` does, so `normalize` is
    # no-opped here rather than mocking `nomad.search` itself, which would require
    # importing that module.
    monkeypatch.setattr(
        'nomad_measurements.xrd.schema.CompositeSystemReference.normalize',
        lambda self, archive, logger: None,
    )
    monkeypatch.setattr(
        'nomad_measurements.xrd.schema.InstrumentReference.normalize',
        lambda self, archive, logger: None,
    )

    archive = EntryArchive(
        m_context=ServerContext(),
        metadata=EntryMetadata(main_author=User(user_id='test-user-id')),
    )
    xrd_dict = {
        'metadata': {
            'sample_id': 'test-sample-id',
            'instrument_id': '0000000011073629',
            'start_time': start_time_input,
        }
    }

    entry = ELNXRayDiffraction()
    entry.write_xrd_data(xrd_dict, archive, structlog.get_logger())

    assert len(entry.samples) == 1
    assert entry.samples[0].lab_id == 'test-sample-id'
    assert len(entry.instruments) == 1
    assert entry.instruments[0].lab_id == '0000000011073629'
    assert entry.datetime == expected_datetime


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
