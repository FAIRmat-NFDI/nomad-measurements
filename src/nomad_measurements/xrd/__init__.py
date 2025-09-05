from nomad.config.models.plugins import ParserEntryPoint, SchemaPackageEntryPoint
from pydantic import Field


class XRDSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    use_hdf5_results: bool = Field(
        default=False,
        description='Whether to use HDF5 results sections by default.',
    )

    def load(self):
        from nomad_measurements.xrd.schema import m_package

        return m_package


schema_entry_point = XRDSchemaPackageEntryPoint(
    name='XRD Schema',
    description='Schema for XRD FAIR data.',
)


class XRDParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.xrd.parser import XRDParser

        return XRDParser(**self.model_dump())


parser_entry_point = XRDParserEntryPoint(
    name='XRD Parser',
    description='Parser for several kinds of raw files from XRD measurements.',
    mainfile_name_re=r'^.*\.xrdml$|^.*\.rasx$|^.*\.brml$',
    mainfile_mime_re='text/.*|application/zip|application/octet-stream',
)
