from nomad.config.models.plugins import (
    ParserEntryPoint,
    SchemaPackageEntryPoint,
)


class DataParserEntryPointETO(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSETOParser

        return PPMSETOParser(**self.dict())


eto_parser = DataParserEntryPointETO(
    name='DataParser for PPMS ETO',
    description="""Parser for PPMS data files created by the ETO option. 
        Parses files containing the 'BYAPP, Electrical Transport Option' line and 
        extracts resistivities, temperatures, fields, and other relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP, Electrical Transport Option',
)


class DataParserEntryPointACT(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSACTParser

        return PPMSACTParser(**self.dict())


act_parser = DataParserEntryPointACT(
    name='DataParser for PPMS ACT',
    description="""Parser for PPMS data files created by the ACT option.
        Parses files containing the 'BYAPP, ACTRANSPORT' (Alternating current
        transport) line and extracts resistivities, temperatures, fields, and other
        relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*ACTRANSPORT',
)


class DataParserEntryPointMPMS(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSMPMSParser

        return PPMSMPMSParser(**self.dict())


mpms_parser = DataParserEntryPointMPMS(
    name='DataParser for PPMS MPMS',
    description="""Parser for PPMS data files created by the MPMS option.
        Parses files containing the 'BYAPP, MPMS' (Magnetic property measurement
        system) line and extracts temperatures, fields, and other relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*MPMS',
)


class DataParserEntryPointResisitivity(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSResistivityParser

        return PPMSResistivityParser(**self.dict())


resistivity_parser = DataParserEntryPointResisitivity(
    name='DataParser for PPMS Resistivity',
    description="""Parser for PPMS data files created by the Resistivity option.
        Parses files containing the 'BYAPP, Resistivity' line and extracts
        resistivities, temperatures, fields, and other relevant data. """,
    mainfile_name_re=r'.+\.dat',
    mainfile_mime_re='text/plain|application/x-wine-extension-ini',
    mainfile_contents_re=r'BYAPP,\s*Resistivity',
)


class DataParserEntryPointACMS(ParserEntryPoint):
    def load(self):
        from nomad_measurements.ppms.parser import PPMSACMSParser

        return PPMSACMSParser(**self.dict())


acms_parser = DataParserEntryPointACMS(
    name='DataParser for PPMS ACMS',
    description="Parser for PPMS data files created by the ACMS option. \
        Parses files containing the 'BYAPP, ACMS' (Alternating current magnetic\
        susceptibility) line and extracts resistivities, temperatures, fields, and \
        other relevant data. ",
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
    description='Parser for PPMS sequence files.',
    mainfile_name_re=r'.+\.seq',
    mainfile_mime_re='text/plain',
)


class PPMSETOEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_eto

        return m_package_ppms_eto


eto_schema = PPMSETOEntryPoint(
    name='PPPMS ETO Schema',
    description='Schema for PPMS measurements done by the ETO option.',
)


class PPMSACTEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_act

        return m_package_ppms_act


act_schema = PPMSACTEntryPoint(
    name='PPMS ACT Schema',
    description='Schema for PPMS measurements done by the ACT option.',
)


class PPMSACMSEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_acms

        return m_package_ppms_acms


acms_schema = PPMSACMSEntryPoint(
    name='PPMS ACMS Schema',
    description='Schema for PPMS measurements done by the ACMS option.',
)


class PPMSMPMSEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_mpms

        return m_package_ppms_mpms


mpms_schema = PPMSMPMSEntryPoint(
    name='PPMS MPMS Schema',
    description='Schema for PPMS measurements done by the MPMS option.',
)


class PPMSResistivityEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements.ppms.schema import m_package_ppms_resistivity

        return m_package_ppms_resistivity


resistivity_schema = PPMSResistivityEntryPoint(
    name='PPMS Resistivity Schema',
    description='Schema for PPMS measurements done by the Resistivity option.',
)
