
from nomad.config.models.plugins import SchemaPackageEntryPoint


class XRDSchemaPackageEntryPoint(SchemaPackageEntryPoint):

    def load(self):
        from nomad_measurements.xrd.schema import m_package

        return m_package


schema = XRDSchemaPackageEntryPoint(
    name='XRDSchema',
    description='Schema package defined using the new plugin mechanism.',
)
