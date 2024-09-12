# How to Use the NOMAD-measurement Plugin

The **NOMAD-measurement plugin** provides standardized schemas for common characterization methods and instruments. These schemas are generalized to ensure they are not tied to any specific lab or setup, promoting interoperability across the materials science community. Users can inherit from these schemas, further specializing them to fit their specific needs, all while maintaining a consistent structure that benefits broader community use. For more details, see [levels of schemas in NOMAD](../explanation/levelsofschema.md).

To use this plugin, you must have it installed on your NOMAD Oasis instance (please refer to the [installation guide](install.md) for instructions). Alternatively, you can explore the plugin’s functionality and make use of it on our centrally hosted [Example Oasis](https://nomad-lab.eu/prod/v1/oasis/gui/search/entries).

This guide will walk you through the different ways to use the NOMAD-measurement plugin:

- **Without specialization**: Instantiating NOMAD entries directly from the "*built-in schemas*".
- **Inheriting and specializing**: Using custom YAML schemas to adapt the existing schemas for your specific use case.
- **Using Python schema plugins**: Inheriting and specializing schemas with Python for advanced customization.

## Using "Built-in Schemas"

In this section, we will demonstrate how to use the standard, built-in schemas provided by the plugin without any specialization. These schemas can be directly instantiated to create entries in NOMAD.

## Inheriting and Specializing Using Custom YAML Schemas

Here, we will guide you through how to extend and specialize the built-in schemas using custom YAML schemas. This approach allows you to tailor the schema to your specific requirements while still leveraging the standardized base provided by the plugin.

## Inheriting and Specializing Using Python Schema Plugins

For users needing more advanced customization, we will show you how to inherit and specialize schemas using Python schema plugins. This method allows for dynamic, programmatic extensions of the standard schemas to accommodate complex use cases.

By following these steps, you can seamlessly integrate the NOMAD-measurement plugin into your workflows and adapt it to meet your specific needs.