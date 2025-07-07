from nomad.config.models.plugins import (
    ParserEntryPoint,
    SchemaPackageEntryPoint,
)


class DataParserEntryPointETO(ParserEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.parser import QDETOParser

        return QDETOParser(**self.model_dump())


eto_parser = DataParserEntryPointETO(
    name='DataParser for QD ETO',
    description="""Parser for QD data files created by the ETO option.
        Parses files containing the 'BYAPP, Electrical Transport Option' line and
        extracts resistivities, temperatures, fields, and other relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP, Electrical Transport Option',
)


class DataParserEntryPointACT(ParserEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.parser import QDACTParser

        return QDACTParser(**self.model_dump())


act_parser = DataParserEntryPointACT(
    name='DataParser for QD ACT',
    description="""Parser for QD data files created by the ACT option.
        Parses files containing the 'BYAPP, ACTRANSPORT' (Alternating current
        transport) line and extracts resistivities, temperatures, fields, and other
        relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*ACTRANSPORT',
)


class DataParserEntryPointMPMS(ParserEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.parser import QDMPMSParser

        return QDMPMSParser(**self.model_dump())


mpms_parser = DataParserEntryPointMPMS(
    name='DataParser for QD MPMS',
    description="""Parser for QD data files created by the MPMS option.
        Parses files containing the 'BYAPP, MPMS' (Magnetic property measurement
        system) line and extracts temperatures, fields, and other relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*MPMS',
)


class DataParserEntryPointResisitivity(ParserEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.parser import QDResistivityParser

        return QDResistivityParser(**self.model_dump())


resistivity_parser = DataParserEntryPointResisitivity(
    name='DataParser for QD Resistivity',
    description="""Parser for QD data files created by the Resistivity option.
        Parses files containing the 'BYAPP, Resistivity' line and extracts
        resistivities, temperatures, fields, and other relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*Resistivity',
)


class DataParserEntryPointACMS(ParserEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.parser import QDACMSParser

        return QDACMSParser(**self.model_dump())


acms_parser = DataParserEntryPointACMS(
    name='DataParser for QD ACMS',
    description="Parser for QD data files created by the ACMS option. \
        Parses files containing the 'BYAPP, ACMS' (Alternating current magnetic\
        susceptibility) line and extracts resistivities, temperatures, fields, and \
        other relevant data. ",
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*ACMS',
)


class SqcParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.parser import QDSequenceParser

        return QDSequenceParser(**self.model_dump())


sequence_parser = SqcParserEntryPoint(
    name='QDSequenceParser',
    description='Parser for QD sequence files.',
    mainfile_name_re=r'.+\.seq',
    mainfile_mime_re='text/plain',
)


class QDETOEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.schema import m_package

        return m_package


eto_schema = QDETOEntryPoint(
    name='PQD ETO Schema',
    description='Schema for QD measurements done by the ETO option.',
)


class QDACTEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.schema import m_package

        return m_package


act_schema = QDACTEntryPoint(
    name='QD ACT Schema',
    description='Schema for QD measurements done by the ACT option.',
)


class QDACMSEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.schema import m_package

        return m_package


acms_schema = QDACMSEntryPoint(
    name='QD ACMS Schema',
    description='Schema for QD measurements done by the ACMS option.',
)


class QDMPMSEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.schema import m_package

        return m_package


mpms_schema = QDMPMSEntryPoint(
    name='QD MPMS Schema',
    description='Schema for QD measurements done by the MPMS option.',
)


class QDResistivityEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.quantumdesign.schema import m_package

        return m_package


resistivity_schema = QDResistivityEntryPoint(
    name='QD Resistivity Schema',
    description='Schema for QD measurements done by the Resistivity option.',
)
