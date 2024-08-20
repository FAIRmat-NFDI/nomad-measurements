from nomad.config.models.plugins import SchemaPackageEntryPoint


class GeneralSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.general.schema import m_package

        return m_package


schema = GeneralSchemaPackageEntryPoint(
    name='GeneralSchema',
    description='Schema package defined using the new plugin mechanism.',
)
