from nomad.config.models.plugins import ParserEntryPoint, SchemaPackageEntryPoint


class XRDSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.xrd.schema import m_package

        return m_package


schema = XRDSchemaPackageEntryPoint(
    name='XRD Schema',
    description='Schema for XRD FAIR data.',
)


class XRDParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.xrd.parser import XRDParser

        return XRDParser(**self.dict())


parser = XRDParserEntryPoint(
    name='XRD Parser',
    description='Parser for several kinds of raw files from XRD measurements.',
    mainfile_name_re=r'^.*\.xrdml$|^.*\.rasx$|^.*\.brml$',
    mainfile_mime_re='text/.*|application/zip',
)


class XRDParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.xrd.parser import XRDParser

        return XRDParser(**self.dict())


parser = XRDParserEntryPoint(
    name='XRD Parser',
    description='Parser for several kinds of raw files from XRD measurements.',
    mainfile_name_re=r'^.*\.xrdml$|^.*\.rasx$|^.*\.brml$',
    mainfile_mime_re='text/.*|application/zip',
)
