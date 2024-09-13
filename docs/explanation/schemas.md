# NOMAD Measurements: a Community plugin

The NOMAD Measurements plugin contains schemas for different measurement methods. 
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

Each method has a dedicated [module](https://docs.python.org/3/tutorial/modules.html), i. e., a python file.

### General
`nomad_measurements.general` module includes --.

### X-Ray Diffraction

`nomad_measurements.xrd.schema` module includes the sections for modeling measurement data
from X-Ray diffraction (XRD). These sections model both the metadata associated with the
setting of the measurement, as well as its results.

In addition to data modeling section, the module contains an ELN (stands for Electronic
Lab Notebook) section, which can be used to create an NOMAD 
[entry](https://nomad-lab.eu/prod/v1/docs/reference/glossary.html#entry) 
for XRD measurement
and populate the data directly from the files coming from the instrument. 
In addition, the section generates plots of XRD patterns using the results.

In this documentation, we go over some of the important sections of this module.
You can access the definitions all the sections in this module by using the 
[metainfo browser](https://nomad-lab.eu/prod/v1/oasis/gui/analyze/metainfo/nomad_measurements)
and seaching for: `"nomad_measurements.xrd"`

#### `XRayDiffraction`
`nomad_measurements.schema.XRayDiffraction` extends 
[`Measurement`](https://nomad-lab.eu/prod/v1/docs/howto/customization/base_sections.html#measurement)
base section and describes the settings and results of XRD measurement. This is achieved
by composing `XRDSettings` and `XRDResult` sections.
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

#### `ELNXRayDiffraction`
`nomad_measurements.schema.ELNXRayDiffraction` allows to use
`XRayDiffraction` as an entry section, which can be used to 
create NOMAD [entries](https://nomad-lab.eu/prod/v1/docs/reference/glossary.html#entry).

The quantity *data_file* can be used to upload a measurement file
coming from the instrument. The section uses readers defined in 
[fairmat-readers-xrd](https://pypi.org/project/fairmat-readers-xrd/) package to extract
data from the file and populate the `XRayDiffraction` schema. Currently, the
the reader package supports reading `.brml`, `.xrdml`, and `.rasx` files. Please check
the package's documentation for an up-to-date list of the supported file types.

It also inherits the 
[`PlotSection`](https://nomad-lab.eu/prod/v1/docs/reference/annotations.html#plot),
which is used to display Plotly figures of the XRD pattern in the NOMAD GUI.





