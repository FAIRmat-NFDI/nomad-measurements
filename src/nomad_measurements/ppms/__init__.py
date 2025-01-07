from nomad.config.models.plugins import (
    ParserEntryPoint,
    SchemaPackageEntryPoint,
)
from pydantic import Field


class DataParserEntryPointETO(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.parser import PPMSETOParser

        return PPMSETOParser(**self.dict())


eto_parser = DataParserEntryPointETO(
    name='DataParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP, Electrical Transport Option',
)


class DataParserEntryPointACT(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.parser import PPMSACTParser

        return PPMSACTParser(**self.dict())


act_parser = DataParserEntryPointACT(
    name='DataParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*ACTRANSPORT',
)


class DataParserEntryPointACMS(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.parser import PPMSACMSParser

        return PPMSACMSParser(**self.dict())


acms_parser = DataParserEntryPointACMS(
    name='DataParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*ACMS',
)


class SqcParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSSequenceParser

        return PPMSSequenceParser(**self.dict())


sequence_parser = SqcParserEntryPoint(
    name='PpmsSequenceParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.+\.seq',
    mainfile_mime_re='text/plain',
)


class PPMSETOEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_eto

        return m_package_ppms_eto


eto_schema = PPMSETOEntryPoint(
    name='PPMSETOEntryPoint',
    description='New schema package entry point configuration.',
)


class PPMSACTEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_act

        return m_package_ppms_act


act_schema = PPMSACTEntryPoint(
    name='PPMSACTEntryPoint',
    description='New schema package entry point configuration.',
)


class PPMSACMSEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_acms

        return m_package_ppms_acms


acms_schema = PPMSACMSEntryPoint(
    name='PPMSACMSEntryPoint',
    description='New schema package entry point configuration.',
)
