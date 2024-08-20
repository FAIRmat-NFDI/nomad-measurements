![](https://github.com/FAIRmat-NFDI/nomad-measurements/actions/workflows/publish.yml/badge.svg)
![](https://img.shields.io/pypi/pyversions/nomad-measurements)
![](https://img.shields.io/pypi/l/nomad-measurements)
![](https://img.shields.io/pypi/v/nomad-measurements)

# NOMAD's Measurements Plugin
This is a plugin for [NOMAD](https://nomad-lab.eu) which contains base sections for
materials science measurements. 

The `nomad_measurements.xrd` module supports
parsing of following vendor-specific file formats:
- `.rasx` (Rigaku)
- `.xrdml` (Malvern Panalytical)
- `.brml` (Bruker)

## Getting started
`nomad-measurements` can be installed from PyPI using `pip`.
Currently we require features in `nomad-lab` which are not published to PyPI.
In order to install these a `--index-url` needs to be provided:
```sh
pip install nomad-measurements --index-url https://gitlab.mpcdf.mpg.de/api/v4/projects/2187/packages/pypi/simple
```
### Setting up your OASIS
Read the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/plugins/plugins.html#add-a-plugin-to-your-nomad) for all details on how to deploy the plugin on your NOMAD instance.

You need to modify the ```nomad.yaml``` configuration file of your NOMAD instance.
To include, for example, the XRD plugin you need to add the following lines, that correspond to loading the entry points available in this package: 

```yaml
plugins:
  include:
    - "nomad_measurements.general:general_schema"
    - "nomad_measurements.xrd:xrd_schema"
    - "nomad_measurements.xrd.parser:xrd_parser"
    - "nomad_measurements.transmission:transmission_schema"
    - "nomad_measurements.transmission:transmission_parser"
 ```

### Development
This code is currently under development and for installing and contributing you should clone the repository:
```sh
git clone git@github.com:FAIRmat-NFDI/nomad-measurements.git
cd nomad-measurements
```

And install the package in editable mode with the development ('dev') dependencies:
```sh
pip install -e .[dev]
```