from nomad.config.models.plugins import SchemaPackageEntryPoint


class MappingSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.mapping.schema import m_package

        return m_package


schema_entry_point = MappingSchemaPackageEntryPoint(
    name='Mapping Schema',
    description='Schema package containing schemas for mapping measurements.',
)
