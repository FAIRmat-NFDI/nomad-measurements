# How to Use This Plugin

This plugin can be used in a NOMAD Oasis instalation..

## Add This Plugin to Your NOMAD instalation

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
