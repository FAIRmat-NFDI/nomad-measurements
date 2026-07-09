#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from nomad.datamodel.metainfo.basesections import (
    Measurement,

)
from nomad.metainfo import (
    Package,
    Quantity,
    Section,
    SubSection,
    MEnum,
)
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
)
from nomad_measurements import NOMADMeasurementsCategory
from nomad_measurements.catalytic_measurement.catalytic_measurement import ReactionConditions, ReactorFilling, add_activity

m_package = Package(name='nomad_catalysis')

class SimpleCatalyticReaction(Measurement, EntryData):
    '''
    Example section for a simple catalytic reaction.
    '''
    m_def = Section(
        categories=[NOMADMeasurementsCategory],
        label='Simple Catalytic Measurement')


    reaction_class = Quantity(
        type=str,
        description="""
        A highlevel classification of the studied reaction.
        """,
        a_eln=dict(component='EnumEditQuantity', props=dict(suggestions=[
            'Oxidation', 'Hydrogenation', 'Dehydrogenation', 'Cracking', 'Isomerisation', 'Coupling']
        )),
        iris=['https://w3id.org/nfdi4cat/voc4cat_0007010'])

    reaction_name = Quantity(
        type=str,
        description="""
        The name of the studied reaction.
        """,
        a_eln=dict(
            component='EnumEditQuantity', props=dict(suggestions=[
                'Oxidation of Ethane', 'Oxidation of Propane',
                'Oxidation of Butane', 'CO hydrogenation', 'Methanol Synthesis', 'Fischer-Tropsch',
                'Water gas shift reaction', 'Ammonia Synthesis', 'Ammonia decomposition'])),
        iris=['https://w3id.org/nfdi4cat/voc4cat_0007009'])

    reaction_condition = SubSection(section_def=ReactionConditions, a_eln=ELNAnnotation(label='Reaction Conditions'))
    reactor_filling = SubSection(section_def=ReactorFilling, a_eln=ELNAnnotation(label='Reactor Filling'))

    def normalize(self, archive, logger):
        super(SimpleCatalyticReaction, self).normalize(archive, logger)

        add_activity(archive)
        if self.reaction_name is not None:
            archive.results.properties.catalytic.reaction.name = self.reaction_name
        if self.reaction_class is not None:
            archive.results.properties.catalytic.reaction.type = self.reaction_class


m_package.__init_metainfo__()
