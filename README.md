![](https://github.com/FAIRmat-NFDI/nomad-measurements/actions/workflows/publish.yml/badge.svg)
![](https://img.shields.io/pypi/pyversions/nomad-measurements)
![](https://img.shields.io/pypi/l/nomad-measurements)
![](https://img.shields.io/pypi/v/nomad-measurements)

# NOMAD's Measurements Plugin
This is a plugin for [NOMAD](https://nomad-lab.eu) which contains base sections for
material processing.

## Getting started
`nomad-measurements` can be installed from PyPI using `pip`:
```sh
pip install nomad-measurements
```
### Setting up your OASIS
Read the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/plugins/plugins.html#add-a-plugin-to-your-nomad) for all details on how to deploy the plugin on your NOMAD instance. 

You need to modify the ```nomad.yaml``` configuration file of your NOMAD instance.
To include, for example, the XRD plugin you need to add the following lines: . 

```yaml
plugins:
  include: 
  - 'parsers/nomad_measurements/xrd'
  options:
    parsers/nomad_measurements/xrd:
      python_package: nomad_measurements.xrd
 ```

### Development
This code is currently under development and for installing and contributing you should clone the repository:
```sh
git clone git@github.com:FAIRmat-NFDI/nomad-measurements.git
cd nomad-measurements
```

And install the package in editable mode:
```sh
pip install -e .
```