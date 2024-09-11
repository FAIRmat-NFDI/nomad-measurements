from nomad.config.models.plugins import ParserEntryPoint, SchemaPackageEntryPoint


class TransmissionSchemaEntryPoint(SchemaPackageEntryPoint):
    """
    Entry point for lazy loading of the Transmission schemas.
    """

    def load(self):
        from nomad_measurements.transmission.schema import m_package

        return m_package


class TransmissionParserEntryPoint(ParserEntryPoint):
    """
    Entry point for lazy loading of the TransmissionParser.
    """

    def load(self):
        from nomad_measurements.transmission.parser import TransmissionParser

        return TransmissionParser(**self.dict())


schema = TransmissionSchemaEntryPoint(
    name='Transmission Schema',
    description='Schema for Transmission Spectrophotometry FAIR data.',
)


parser = TransmissionParserEntryPoint(
    name='Transmission Parser',
    description='Parser for raw files from Transmission measurements.',
    mainfile_name_re='^.*\.asc$',
    mainfile_mime_re='text/.*|application/zip',
)
