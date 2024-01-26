from nomad.datamodel.metainfo.basesections import (
    Measurement,
)

from nomad.metainfo.metainfo import (
    Section,
)


class UVIRSpectroscopy(Measurement):
    '''
    A section for UVIR spectroscopy.
    '''
    m_def = Section(
        label='UV-Vis spectroscopy',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        '''
        The normalize function of the `UVIRSpectroscopy` section.
        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)

