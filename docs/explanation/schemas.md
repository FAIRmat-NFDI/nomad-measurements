# NOMAD-measurements: a Community plugin

The NOMAD-measurements plugin contains schemas for different measurement methods.
An overview of the package structure is shown below.

## Technical description

There are some technical aspects to understand the Python package built for this plugin, they are not crucial for the data model understanding itself:

- It is structured according to the [src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).
- It is a [regular Python package](https://docs.python.org/3/reference/import.html#regular-packages), i. e., the structure is defined by the presence of `__init__.py` files. Each of these files contains one or multiple [entry points](https://nomad-lab.eu/prod/v1/staging/docs/howto/plugins/plugins.html#plugin-entry-points). These are used to load a portion of the code within your NOMAD through a specific section in the `nomad.yaml` file.
- It is pip installable. The `project.toml` file defines what will be installed, the dependencies, further details. The **entry points** included are listed in this file.

```text
nomad-measurements/
├── docs
├── pyproject.toml
├── README.md
├── src
│   └── nomad_measurements
│       ├── general.py
│       ├── __init__.py
│       ├── utils.py
│       ├── xrd
│       |   ├── __init__.py
│       |   ├── parser.py
│       |   └── schema.py
|       └── transmission
│           ├── __init__.py
│           ├── parser.py
│           └── schema.py
└── tests
```

## Data model description

Each method has a dedicated [module](https://docs.python.org/3/tutorial/modules.html),
i. e., a python file.

### General
`nomad_measurements.general` module contains `NOMADMeasurementsCategory` which is a
category section that can be used to club together the entry sections of
`nomad_measurements`. A key benefit of using category is that all entry sections appear
under the one label in the drop-down menu of `Create new entry from schema` dialog in
NOMAD Oasis.

If you want extend one of our entry sections with your specifications, and want to add
it under the same category, add this category section in the `m_def` of the extended
section. Here's an example code snippet:
```py
from nomad.metainfo import Section
from nomad_measurements.general import NOMADMeasurementsCategory
from nomad_measurements.xrd.schema import ELNXRayDiffraction

class MyELNXRayDiffraction(ELNXRayDiffraction):
    m_def = Section(
        categories=[NOMADMeasurementsCategory],
    )
    # ... your specifications
```
The general module also contains `ActivityReference` and `ProcessReference` sections.
`ActivityReference` can be used in your schemas to make
[references](https://nomad-lab.eu/prod/v1/docs/howto/plugins/schema_packages.html#references-and-proxies)
to the `Measurement`
entries. It allows to search an existing entry based on its *lab_id*, which is
an inherited quantity in all `Measurement` sections, and automatically make a reference
to it.

### X-Ray Diffraction

`nomad_measurements.xrd.schema` module provides data models for X-Ray diffraction
(XRD). These sections can be used to model the metadata related to the
setting and results of the measurement.

In addition to data modeling section, the module contains an ELN (stands for Electronic
Lab Notebook) section, which can be used to create an NOMAD
[entry](https://nomad-lab.eu/prod/v1/docs/reference/glossary.html#entry)
for XRD measurement
and populate the data directly from the files coming from the instrument.
The section also provides methods to generate plots for XRD patterns.

In this documentation, we go over some of the important sections of this module.
Alternatively, you can access all the section definitions by using the
[metainfo browser](https://nomad-lab.eu/prod/v1/oasis/gui/analyze/metainfo/nomad_measurements)
and searching for: `"nomad_measurements.xrd"`

#### `XRayDiffraction`

`nomad_measurements.xrd.schema.XRayDiffraction` section extends
[`Measurement`](https://nomad-lab.eu/prod/v1/docs/howto/customization/base_sections.html#measurement)
base section and describes the settings and results of XRD measurement. This is achieved
by composing `XRDSettings` and `XRDResult` sections as sub-sections.
```py
class XRayDiffraction(Measurement):
    diffraction_method_name: str
    xrd_settings: XRDSettings
    results: list[XRDResult]
```
Once the section is populated, diffraction pattern is indexed under
`properties.structural` field of entry's
[results](https://nomad-lab.eu/prod/v1/docs/reference/glossary.html#results-section-results)
section, making it searchable in NOMAD.

#### `XRDResult`
`nomad_measurements.xrd.schema.XRDResult` section describes results coming from XRD
measurement. These include intensity, two theta, omega, phi, norm of q-vector,
scan axis, and integration time. Their descriptions can be found here in the
[metainfo browser](https://nomad-lab.eu/prod/v1/oasis/gui/analyze/metainfo/nomad_measurements/section_definitions@nomad_measurements.xrd.schema.XRDResult).

The module also contains extension of this section, specifically `XRDResult1D` and
`XRDResultRSM`. `XRDResult1D` provides `generate_plots` method which uses the results
to generate intensity-vs-two-theta and intensity-vs-q-norm plots for line scans.

`XRDResultRSM` extends the
data model to describe reciprocal space maps, or RSM. It redefines shape of *intensity*
to be 2D array and adds two new quantities: *q_parallel* and *q_perpedicular*, each
being a 2D array. Together, these can be used to describe intensity values in a
2D reciprocal space. The section also provides `generate_plots` method to generate
2D surface plot for intensity-vs-two-theta-omega and intensity-vs-q-vectors.

We also have HDF5 versions of these result sections that make use of `HDF5Reference` quantities: `XRDResult1DHDF5` and
`XRDResultRSMHDF5`. More about them [here](#hdf5-references-in-x-ray-diffraction-elns).

#### `XRDSettings`
`nomad_measurements.xrd.schema.XRDSettings` section defines the settings related to the
X-ray source. It composes `XRDTubeSource` section which describes tube material, current
, voltage, *k*<sub>&alpha;<sub>1</sub></sub>, *k*<sub>&alpha;<sub>2</sub></sub>, *k*<sub>&beta;</sub>, and
*k*<sub>&alpha;<sub>1</sub></sub>/*k*<sub>&alpha;<sub>2</sub></sub>

#### `ELNXRayDiffraction`

`nomad_measurements.xrd.schema.ELNXRayDiffraction` section allows to use
`XRayDiffraction` as an entry section, which can be used to
create NOMAD [entries](https://nomad-lab.eu/prod/v1/docs/reference/glossary.html#entry).

The quantity *data_file* can be used to upload a measurement file
coming from the instrument. The section uses readers defined in
[fairmat-readers-xrd](https://pypi.org/project/fairmat-readers-xrd/) package to extract
data from the file and populate the `XRayDiffraction` schema. Currently, the
the reader package supports reading `.brml`, `.xrdml`, and `.rasx` files. Please check
the package's
[documentation](https://github.com/FAIRmat-NFDI/readers-xrd?tab=readme-ov-file#fairmat-readers-xrd)
for an up-to-date list of the supported file types.

It also inherits the
[`PlotSection`](https://nomad-lab.eu/prod/v1/docs/reference/annotations.html#plot),
which allows to display Plotly figures of the XRD pattern in the NOMAD Oasis. The plots
are generated using the `generate_plots` methods of [`XRDResult`](#xrdresult) sections.


### Transmission Spectrophotometry
`nomad_measurements.transmission.schema` provides NOMAD schemas for modeling
data and metadata from transmission spectrophotometry. Currently, schemas
specific to UV-Vis-NIR transmission are available. The module follows a class
structure similar to the [xrd module](#x-ray-diffraction). The
`UVVisNirTransmission` class can be composed using sub-sections for results and
settings. `ELNUVVisNirTransmission` inherits `UVVisNirTransmission` and can be
used to create NOMAD entries for the measurement.

In addition, the module provides classes for modeling the instrument and its
components: `Spectrophotometer`, `Detector`, `LightSource`, and `Monochromator`.
These can be used to model data related to the instrument in a separate entry
that can be referenced in the measurement entry under the `instruments`
sub-section. As the instrument settings are measurement-specific, they should
be modeled in the measurement entry under the `transmission_settings`
sub-section.

When a measurement file of a supported file type is added to a NOMAD upload,
an `ELNUVVisNirTransmission` entry will be generated and populated with data
from the file. If the instrument serial number is available in the file, an
existing instrument entry containing the same serial number is automatically
referenced in the measurement entry.

`ELNUVVisNirTransmission` uses readers defined in
[fairmat-readers-transmission](https://pypi.org/project/fairmat-readers-transmission/) package to extract
data from the file and populate the schema. Currently, the reader package supports reading `.asc` files generated by Perkin Elmer UV WinLab software. Please check
the package's
[documentation](https://github.com/FAIRmat-NFDI/readers-transmission?tab=readme-ov-file#fairmat-readers-transmission)
for an up-to-date list of the supported file types.

You can access all the section definitions by using the
[metainfo browser](https://nomad-lab.eu/prod/v1/oasis/gui/analyze/metainfo/nomad_measurements)
and searching for: `"nomad_measurements.transmission"`.


## HDF5 References

We make use of [`HDF5Reference`](https://nomad-lab.eu/prod/v1/docs/howto/customization/hdf5.html#hdf5reference) as a quantity type in some schemas. These quantities allow to store large datasets in an external `.h5` file, while only storing references to the HDF5 datasets in the NOMAD entry. As a result, the users can connect large datasets to ELN entries without sacrificing their responsiveness.

### HDF5 References in X-Ray Diffraction ELNs

In our ELN schemas for XRD, we allow the user to switch between result sections
using `HDF5Reference`. The user can switch between an HDF5 or a non-HDF5 result
section by clicking the button `Switch To/From HDF5 Results`. When the result
section is switched to an HDF5 one, a NeXus file is generated (which is a `.h5`
file with additional validations) and results are written there. The entry only
stores the references to these HDF5 datasets in the NeXus file. The same button
can be used to switch back to a non-HDF5 result section if needed.

An oasis administrator can also set in the `nomad.yaml` whether to use the HDF5
or non-HDF5 result section when parsing XRD data in the entry for the first
time. Users who usually work with RSM or high-resolution XRD scans can opt-in
to this. Otherwise, the parsed entries use a non-HDF5 result section by default.
```yaml
# "nomad.yaml" file for your oasis
plugins:
entry_points:
    options:
    'nomad_measurements.xrd:schema':
        use_hdf5_results: true # defaults to `false` when not specified
```

### Working with downloaded entries

If the entries using HDF5 result sections are downloaded over the API,
accessing the data of the quantity requires an additional step. The entry only
stores a reference path (`str`) to the data. Make use of the util function
`nomad_measurements.utils.resolve_hdf5_reference` to resolve these paths.

```py
from nomad.client import ArchiveQuery
from nomad_measurements.utils import resolve_hdf5_reference

aq = ArchiveQuery(
    query={'entry_id:any': ['F-b8Bw-kpjKfq']},
    url='http://nomad-lab.eu/prod/v1/oasis/api',
)
xrd = aq.download()[0].data

print(xrd.results[0].intensity)
print(xrd.results[0].two_theta)
# "/uploads/<upload_id>/raw/xrd_example.nxs#/entry/experiment_result/intensity"
# "/uploads/<upload_id>/raw/xrd_example.nxs#/entry/experiment_result/intensity"

intensity, two_theta = resolve_hdf5_reference(
    reference=[
        xrd.results[0].intensity,
        xrd.results[0].two_theta,
    ],
    archive=xrd,
) # resolves the references and returns the XRD data
```
