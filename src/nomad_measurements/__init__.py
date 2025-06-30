from nomad.config.models.plugins import SchemaPackageEntryPoint


class GeneralSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.general import m_package

        return m_package


schema_entry_point = GeneralSchemaPackageEntryPoint(
    name='General Schema',
    description='Schema package containing basic classes used around in the plugin.',
)
