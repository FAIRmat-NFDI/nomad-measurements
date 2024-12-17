from nomad.config.models.plugins import (
    ParserEntryPoint,
    SchemaPackageEntryPoint,
)
from pydantic import Field


class DataParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSParser

        return PPMSParser(**self.dict())


ppms_data_parser = DataParserEntryPoint(
    name='PpmsDataParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='application/x-wine-extension-ini',
)


class SqcParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSSequenceParser

        return PPMSSequenceParser(**self.dict())


ppms_sequence_parser = SqcParserEntryPoint(
    name='PpmsSequenceParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.+\.seq',
    mainfile_mime_re='text/plain',
)


class PPMSSchemaEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.schema import m_package

        return m_package


ppms_schema = PPMSSchemaEntryPoint(
    name='NewSchemaPackage',
    description='New schema package entry point configuration.',
)
