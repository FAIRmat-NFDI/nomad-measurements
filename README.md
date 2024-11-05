![](https://github.com/FAIRmat-NFDI/nomad-measurements/actions/workflows/publish.yml/badge.svg)
![](https://img.shields.io/pypi/pyversions/nomad-measurements)
![](https://img.shields.io/pypi/l/nomad-measurements)
![](https://img.shields.io/pypi/v/nomad-measurements)
[![DOI](https://zenodo.org/badge/687933583.svg)](https://zenodo.org/doi/10.5281/zenodo.13789632)

# NOMAD's Measurements Plugin
This is a plugin for [NOMAD](https://nomad-lab.eu) which contains base sections for
materials science measurements. 

The `nomad_measurements.xrd` module supports
parsing of following vendor-specific file formats:
- `.rasx` (Rigaku)
- `.xrdml` (Malvern Panalytical)
- `.brml` (Bruker)

The `nomad_measurements.ppms` module supports
parsing of following file format:
- `.dat` (in the structure of the QuantumDesign PPMS)

## Getting started
`nomad-measurements` can be installed from PyPI using `pip`.
Currently we require features in `nomad-lab` which are not published to PyPI.
In order to install these a `--index-url` needs to be provided:
```sh
pip install nomad-measurements --index-url https://gitlab.mpcdf.mpg.de/api/v4/projects/2187/packages/pypi/simple
```
### Setting up your OASIS
Read the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/plugins/plugins.html#add-a-plugin-to-your-nomad) for all details on how to deploy the plugin on your NOMAD instance.

You don't need to modify the ```nomad.yaml``` configuration file of your NOMAD instance, beacuse the package is pip installed and all the available modules (entry points) are loaded.
To include, instead, only some of the entry points, you need to specify them in the ```include``` section of the ```nomad.yaml```. In the following lines, a list of all the available entry points:  

```yaml
plugins:
  include:
    - "nomad_measurements.general:schema"
    - "nomad_measurements.xrd:schema"
    - "nomad_measurements.xrd.parser:parser"
    - "nomad_measurements.transmission:schema"
    - "nomad_measurements.transmission:parser"
 ```

### Development
This code is currently under development and for installing and contributing you should clone the repository:
```sh
git clone git@github.com:FAIRmat-NFDI/nomad-measurements.git
cd nomad-measurements
```

And install the package in editable mode with the development ('dev') dependencies:
```sh
pip install -e .[dev] --index-url https://gitlab.mpcdf.mpg.de/api/v4/projects/2187/packages/pypi/simple
```
