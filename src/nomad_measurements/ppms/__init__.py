from nomad.config.models.plugins import (
    ParserEntryPoint,
    SchemaPackageEntryPoint,
)
from pydantic import Field


class DataParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.parser import PPMSParser

        return PPMSParser(**self.dict())


parser_entry_point_data = DataParserEntryPoint(
    name='DataParser',
    description='New parser entry point configuration.',
    mainfile_name_re='^.+\.dat$',
    mainfile_mime_re='application/x-wine-extension-ini',
)


class SqcParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.parser import PPMSSequenceParser

        return PPMSSequenceParser(**self.dict())


parser_entry_point_sqc = SqcParserEntryPoint(
    name='SequenceParser',
    description='New parser entry point configuration.',
    mainfile_name_re='^.+\.seq$',
    mainfile_mime_re='text/plain',
)


class PPMSSchemaEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.schema import m_package

        return m_package


schema_package_entry_point = PPMSSchemaEntryPoint(
    name='NewSchemaPackage',
    description='New schema package entry point configuration.',
)
