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
│       └── xrd
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

`nomad_measurements.schema.XRayDiffraction` section extends 
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
`nomad_measurements.schema.XRDResult` section describes results coming from XRD
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

#### `XRDSettings`
`nomad_measurements.schema.XRDSettings` section defines the settings related to the 
X-ray source. It composes `XRDTubeSource` section which describes tube material, current
, voltage, $k_{{\alpha}_{1}}$, $k_{{\alpha}_{2}}$, $k_{\beta}$, and 
$\frac{k_{{\alpha}_{1}}}{k_{{\alpha}_{2}}}$.

#### `ELNXRayDiffraction`

`nomad_measurements.schema.ELNXRayDiffraction` section allows to use
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





