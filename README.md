# nomad-measurements
A NOMAD plugin containing base sections for measurements. 

## Getting started
This code is currently under development and can be installed by cloning the repository:
```sh
git clone git@github.com:FAIRmat-NFDI/nomad-measurements.git
cd nomad-measurements
```

And installing the package in editable mode:
```sh
pip install -e . --index-url https://gitlab.mpcdf.mpg.de/api/v4/projects/2187/packages/pypi/simple
```

**Note!**
Until we have an official pypi NOMAD release with the plugins functionality. Make
sure to include NOMAD's internal package registry (via `--index-url`).
```

This plugin is  work in progress and an initial test. At the moment is only supporting `.xrdml` files.

There are conflicting dependencies with the current NOMAD `develop` branch.
To test it in dev mode, you need to do the following in your NOMAD installation:

```python
pip install xrayutilities
pip install numpy==1.24.3
pip install numba --upgrade
```
You might get some complains saying that `scipy` needs to be upgraded too, but this should get the plugin working.

Read the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/plugins/plugins.html#add-a-plugin-to-your-nomad) for all details on how to deploy the plugin on your NOMAD instance. 

You need to modify the ```nomad.yaml``` configuration file of your NOMAD instance. Add the following lines: . 

```yaml
keycloak:
  realm_name: fairdi_nomad_test
plugins:
  # We only include our schema here. Without the explicit include, all plugins will be
  # loaded. Many build in plugins require more dependencies. Install nomad-lab[parsing]
  # to make all default plugins work.
  include: 
  - 'schemas/nomad_measurements/xrd'
  options:
    schemas/nomad_measurements/xrd:
      python_package: nomad_measurements.xrd
 ```