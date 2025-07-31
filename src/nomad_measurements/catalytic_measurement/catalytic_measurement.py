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
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from nomad.datamodel.metainfo.basesections import (
    PubChemPureSubstanceSection,
    CompositeSystem, CompositeSystemReference
)

from nomad.metainfo import (
    Quantity,
    Section,
    SubSection,
    Datetime,
)
from nomad.units import ureg

from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.results import (
    Results,
    Properties,
    CatalyticProperties,
    Reaction,
    Reactant
)
from nomad.datamodel.metainfo.plot import (
    PlotSection,
    PlotlyFigure,
)

from nomad_measurements import NOMADMeasurementsCategory

def add_activity(archive):
    '''Adds metainfo structure for catalysis activity test data.'''
    if not archive.results:
        archive.results = Results()
    if not archive.results.properties:
        archive.results.properties = Properties()
    if not archive.results.properties.catalytic:
        archive.results.properties.catalytic = CatalyticProperties()
    if not archive.results.properties.catalytic.reaction:
        archive.results.properties.catalytic.reaction = Reaction()

# class CatalystSample(CompositeSystem, EntryData):
#     '''Example section for a catalyst sample.'''
#     m_def = Section(
#         categories=[NOMADMeasurementsCategory],
#         label='Catalyst Sample')


class Reagent(ArchiveSection):
    m_def = Section(label_quantity='name', description='a chemical substance present in the initial reaction mixture')
    name = Quantity(type=str, a_eln=ELNAnnotation(label='reagent name', component='StringEditQuantity'), description="reagent name")
    gas_concentration_in = Quantity(
        type=np.float64,
        description='Volumetric fraction of a reagent in the feed gas.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'))
    flow_rate = Quantity(
        type=np.float64, unit='mL/minute',
        description='Flow rate of reactant in feed gas.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'))

    pure_reagent = SubSection(section_def=PubChemPureSubstanceSection)


    def normalize(self, archive, logger: 'BoundLogger') -> None:
        '''
        The normalizer for the `PureSubstanceComponent` class. If none is set, the
        normalizer will set the name of the component to be the molecular formula of the
        substance.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger ('BoundLogger'): A structlog logger.
        '''
        super(Reagent, self).normalize(archive, logger)

        if self.name and self.pure_reagent is None:
            self.pure_reagent = PubChemPureSubstanceSection(
                name=self.name
            )
            self.pure_reagent.normalize(archive, logger)

        if self.pure_reagent is not None and self.pure_reagent.iupac_name is None:
            print(self.pure_reagent.molecular_formula)
            if self.pure_reagent.molecular_formula == 'CO2':
                self.pure_reagent.iupac_name = 'carbon dioxide'

        if self.name == "CO" or self.name == "carbon monoxide":
            self.pure_reagent.iupac_name = 'carbon monoxide'
            self.pure_reagent.molecular_formula = 'CO'
            self.pure_reagent.molecular_mass = 28.01
            self.pure_reagent.smile = 'C#O'
            self.pure_reagent.inchi = 'InChI=1S/CO/c1-2'
            self.pure_reagent.inchi_key = 'UGFAIRIUMAVXCW-UHFFFAOYSA-N'
            self.pure_reagent.cas_number = '630-08-0'

        if self.name is None and self.pure_reagent is not None:
            self.name = self.pure_reagent.molecular_formula


class CatalyticSectionConditions_static(ArchiveSection):
    m_def = Section(description='A class containing reaction conditions of a single run or set of conditions.')

    repeat_settings_for_next_run = Quantity(
        type=bool, a_eln=ELNAnnotation(component='BoolEditQuantity'))

    set_temperature = Quantity(
        type=np.float64, unit='K', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    set_pressure = Quantity(
        type=np.float64, unit='bar', a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='bar'))

    set_total_flow_rate = Quantity(
        type=np.float64, unit='mL/minute', a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='mL/minute'))

    duration = Quantity(
        type=np.float64, unit='hour', a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='hour'))

    weight_hourly_space_velocity = Quantity(
        type=np.float64, unit='mL/(g*hour)', a_eln=dict(component='NumberEditQuantity'))

    contact_time = Quantity(
        type=np.float64, unit='g*s/mL', a_eln=ELNAnnotation(label='W|F', component='NumberEditQuantity'))

    gas_hourly_space_velocity = Quantity(
        type=np.float64, unit='1/hour', a_eln=dict(component='NumberEditQuantity'))

    datetime = Quantity(
        type=Datetime,
        description='The date and time when this activity was started.',
        a_eln=ELNAnnotation(component='DateTimeEditQuantity', label='Starting Time'))

    time_on_stream = Quantity(
        type=np.float64, unit='hour', a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='hour'))

    description = Quantity(
        type=str, a_eln=dict(component='RichTextEditQuantity'))

    reagents = SubSection(section_def=Reagent, repeats=True)

    def normalize(self, archive, logger):
        super(CatalyticSectionConditions_static, self).normalize(archive, logger)

        for reagent in self.reagents:
            if reagent is None:
                raise ValueError('No reagents are defined')
            reagent.normalize(archive, logger)

        if self.set_total_flow_rate is None and self.reagents is not None:
            total_flow_rate=0
            for reagent in self.reagents:
                if reagent.flow_rate is not None:
                    total_flow_rate+=reagent.flow_rate
            self.set_total_flow_rate=total_flow_rate

        if self.set_total_flow_rate is not None:
           for reagent in self.reagents:
                if reagent.flow_rate is None and reagent.gas_concentration_in is not None:
                    reagent.flow_rate = self.set_total_flow_rate * reagent.gas_concentration_in

        if self.m_parent.catalyst is not None or self.m_root().data.reactor_filling is not None:
            if self.m_parent.catalyst is not None:
                if self.m_parent.catalyst.catalyst_mass is not None:
                    if self.weight_hourly_space_velocity is None and self.set_total_flow_rate is not None:
                        self.weight_hourly_space_velocity = self.set_total_flow_rate / self.m_parent.catalyst.catalyst_mass
                    if self.contact_time is None and self.set_total_flow_rate is not None:
                        self.contact_time = self.m_parent.catalyst.catalyst_mass / self.set_total_flow_rate
            elif self.m_root().data.reactor_filling.catalyst_mass is not None:
                if self.weight_hourly_space_velocity is None and self.set_total_flow_rate is not None:
                    self.weight_hourly_space_velocity = self.set_total_flow_rate / self.m_root().data.reactor_filling.catalyst_mass
                if self.contact_time is None and self.set_total_flow_rate is not None:
                    self.contact_time = self.m_root().data.reactor_filling.catalyst_mass / self.set_total_flow_rate


class CatalyticSectionConditions_dynamic(CatalyticSectionConditions_static):
    m_def = Section(description='A class containing reaction conditions of a generic reaction with changing conditions.')

    set_temperature = Quantity(
        type=np.float64, unit='K', a_eln=dict(label='Set temperature section start', component='NumberEditQuantity'))

    set_temperature_section_stop = Quantity(
        type=np.float64, unit='K', a_eln=dict(component='NumberEditQuantity'))

    set_pressure = Quantity(
        type=np.float64, unit='bar', a_eln=dict(label='Set pressure section start', component='NumberEditQuantity', defaultDisplayUnit='bar'))

    set_pressure_section_stop = Quantity(
        type=np.float64, unit='bar', a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='bar'))


class ReactorFilling(ArchiveSection):
    m_def = Section(description='A class containing information about the catalyst and filling in the reactor.')

    catalyst_name = Quantity(
        type=str, shape=[], a_eln=ELNAnnotation(component='StringEditQuantity'))

    sample_reference = Quantity(
        type=CompositeSystem, description='A reference to the sample used for the measurement.',
        a_eln=ELNAnnotation(component='ReferenceEditQuantity', label='Entity Reference'))

    catalyst_mass = Quantity(
        type=np.float64, shape=[], unit='mg', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    catalyst_density = Quantity(
        type=np.float64, shape=[], unit='g/mL', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    apparent_catalyst_volume = Quantity(
        type=np.float64, shape=[], unit='mL', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    catalyst_sievefraction_upper_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))
    catalyst_sievefraction_lower_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))
    particle_size = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))
    diluent = Quantity(
        type=str,
        shape=[],
        description="""
        A component that is mixed with the catalyst to dilute and prevent transport
        limitations and hot spot formation.
        """,
        a_eln=dict(component='EnumEditQuantity', props=dict(
            suggestions=['SiC', 'SiO2', 'unknown']))
    )
    diluent_sievefraction_upper_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))
    diluent_sievefraction_lower_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))

    def normalize(self, archive, logger):
        super(ReactorFilling, self).normalize(archive, logger)

        if self.sample_reference is None:
            if self.m_root().data.samples != []:
                self.sample_reference = self.m_root().data.samples[0].reference
        if self.sample_reference is not None:
            if self.m_root().data.samples == []:
                sample1_reference = CompositeSystemReference(reference=self.sample_reference)
                self.m_root().data.samples.append(sample1_reference)
            elif self.m_root().data.samples.reference is None:
                self.m_root().data.samples.reference = self.sample_reference
            self.sample_reference.normalize(archive, logger)

        if self.catalyst_name is None and self.sample_reference is not None:
            self.catalyst_name = self.sample_reference.name

        if self.apparent_catalyst_volume is None and self.catalyst_mass is not None and self.catalyst_density is not None:
            self.apparent_catalyst_volume = self.catalyst_mass / self.catalyst_density


class ReactionConditions(PlotSection, ArchiveSection):
    m_def = Section(description='A class containing reaction conditions for a generic reaction.')

    number_of_sections = Quantity(
        type=np.int32,
        description='The number of sections with different reaction conditions.',
        a_eln=dict(component='NumberEditQuantity'))

    total_time_on_stream = Quantity(
        type=np.float64, unit='hour', a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='hour'))

    section_runs = SubSection(section_def=CatalyticSectionConditions_static, repeats=True)
    catalyst = SubSection(section_def=ReactorFilling, repeats=False)    # moved up in entry; if not used could be removed?

    def normalize(self, archive, logger):
        super(ReactionConditions, self).normalize(archive, logger)


        if self.section_runs is not None:
            for i,run in enumerate(self.section_runs):
                if run.repeat_settings_for_next_run is True:
                    try:
                        if self.section_runs[i+1] is None:
                            self.section_runs.append(CatalyticSectionConditions_static())
                    except IndexError:
                        self.section_runs.append(CatalyticSectionConditions_static())
                    if run.set_temperature is not None and self.section_runs[i+1].set_temperature is None:
                        self.section_runs[i+1].set_temperature = run.set_temperature
                    if run.set_pressure is not None and self.section_runs[i+1].set_pressure is None:
                        self.section_runs[i+1].set_pressure = run.set_pressure
                    if run.set_total_flow_rate is not None and self.section_runs[i+1].set_total_flow_rate is None:
                        self.section_runs[i+1].set_total_flow_rate = run.set_total_flow_rate
                    if run.duration is not None and self.section_runs[i+1].duration is None:
                        self.section_runs[i+1].duration = run.duration
                    if run.weight_hourly_space_velocity is not None and self.section_runs[i+1].weight_hourly_space_velocity is None:
                        self.section_runs[i+1].weight_hourly_space_velocity = run.weight_hourly_space_velocity
                    if run.contact_time is not None and self.section_runs[i+1].contact_time is None:
                        self.section_runs[i+1].contact_time = run.contact_time
                    if run.gas_hourly_space_velocity is not None and self.section_runs[i+1].gas_hourly_space_velocity is None:
                        self.section_runs[i+1].gas_hourly_space_velocity = run.gas_hourly_space_velocity
                    if run.reagents is not None and self.section_runs[i+1].reagents == []:
                        reagents_next=[]
                        for reagent in run.reagents:
                            reagents_next.append(reagent)
                        self.section_runs[i+1].reagents = reagents_next

            time=0
            for run in self.section_runs:
                if run.duration is not None:
                    time = time + run.duration
                    run.time_on_stream = time
                self.total_time_on_stream = time

            self.number_of_sections = len(self.section_runs)


        add_activity(archive)
        for run in self.section_runs:
            run.normalize(archive, logger)

        #convert single value in run quantity to list
        if self.section_runs is not None:
            temperature_list = np.array([])
            pressure_list = np.array([])
            total_flow_rate_list = np.array([])
            weight_hourly_space_velocity_list = np.array([])
            gas_hourly_space_velocity_list = np.array([])
            time_on_stream_list = np.array([])

            for n,run in enumerate(self.section_runs):
                if run.set_temperature is not None:
                    temperature_list=np.append(temperature_list, run.set_temperature)
                if run.set_pressure is not None:
                    pressure_list=np.append(pressure_list, run.set_pressure)
                if run.set_total_flow_rate is not None:
                    total_flow_rate_list=np.append(total_flow_rate_list, run.set_total_flow_rate)
                if run.weight_hourly_space_velocity is not None:
                    weight_hourly_space_velocity_list=np.append(weight_hourly_space_velocity_list, run.weight_hourly_space_velocity)
                if run.gas_hourly_space_velocity is not None:
                    gas_hourly_space_velocity_list=np.append(gas_hourly_space_velocity_list, run.gas_hourly_space_velocity)
                if run.time_on_stream is not None:
                    time_on_stream_list = np.append(time_on_stream_list, run.time_on_stream)

            if temperature_list.any():
                archive.results.properties.catalytic.reaction.temperature = temperature_list
            if pressure_list.any():
                archive.results.properties.catalytic.reaction.pressure = pressure_list
            if total_flow_rate_list.any():
                archive.results.properties.catalytic.reaction.flow_rate = total_flow_rate_list
            if weight_hourly_space_velocity_list.any():
                archive.results.properties.catalytic.reaction.weight_hourly_space_velocity = weight_hourly_space_velocity_list
            if gas_hourly_space_velocity_list.any():
                archive.results.properties.catalytic.reaction.gas_hourly_space_velocity = gas_hourly_space_velocity_list
            if time_on_stream_list.any():
                archive.results.properties.catalytic.reaction.time_on_stream = time_on_stream_list
            if self.total_time_on_stream is not None:
                archive.results.properties.catalytic.reaction.total_time_on_stream = self.total_time_on_stream

            if self.section_runs[0].reagents is not None:
                reactants=[]
                for r in self.section_runs[0].reagents:
                    print(r.name)
                    gas_concentration_in = np.array([])
                    for run in self.section_runs:
                        if run.reagents is not None:
                            for reagent in run.reagents:
                                if reagent.name == r.name:
                                    if reagent.pure_reagent is not None:
                                        if reagent.pure_reagent.iupac_name is not None:
                                            name = reagent.pure_reagent.iupac_name
                                        else:
                                            name = reagent.name
                                    gas_concentration_in = np.append(gas_concentration_in, reagent.gas_concentration_in)
                    reactant = Reactant(name=name, gas_concentration_in=gas_concentration_in)
                    reactants.append(reactant)
                archive.results.properties.catalytic.reaction.reactants = reactants

        #Figures definitions:
        self.figures = []
        if self.section_runs is not None:
            figT=go.Figure()
            x=[0,]
            y=[]
            for i,run in enumerate(self.section_runs):
                if run.set_temperature is not None:
                    y.append(run.set_temperature.to('kelvin'))
                    try:
                        if run.set_temperature_section_stop is not None:
                            y.append(run.set_temperature_section_stop.to('kelvin'))
                    except:
                        y.append(run.set_temperature.to('kelvin'))
                if run.set_pressure is not None:
                    if i == 0:
                        figP=go.Figure()
                        y_p=[]
                    y_p.append(run.set_pressure.to('bar'))
                    try:
                        if run.set_pressure_section_stop is not None:
                            y_p.append(run.set_pressure_section_stop.to('bar'))
                    except:
                        y_p.append(run.set_pressure.to('bar'))
                if run.time_on_stream is not None:
                    x.append(run.time_on_stream.to('hour'))
                    if i != len(self.section_runs)-1:
                        x.append(run.time_on_stream.to('hour'))
                    x_text="time (h)"
                elif i == len(self.section_runs)-1:
                    for j in range(1, len(self.section_runs)):
                        x.append(j)
                        if j != len(self.section_runs)-1:
                            x.append(j)
                    x_text='step'
                if run.reagents != []:
                    for n,reagent in enumerate(run.reagents):
                        if n == 0 and i == 0:
                            figR=go.Figure()
                            reagent_n, runs_n = (len(run.reagents), len(self.section_runs))
                            y_r=[[0 for k in range(2*runs_n)] for l in range(reagent_n+1) ]
                            reagent_name=[0 for k in range(reagent_n+1)]
                        if i==0:
                            reagent_name[n]=reagent.name
                            if n == len(run.reagents)-1:
                                reagent_name[n+1]=['total flow rate']
                        if reagent.flow_rate is not None:
                            if reagent.name == reagent_name[n]:
                                y_r[n][2*i]=(reagent.flow_rate.to('mL/minute'))
                                y_r[n][2*i+1]=(reagent.flow_rate.to('mL/minute'))
                                y_r_text="Flow rates (mL/min)"
                            else:
                                logger.warning('Reagent name has changed in run'+str(i+1)+'.')
                                return
                            if n == len(run.reagents)-1:
                                y_r[n+1][2*i]=(run.set_total_flow_rate.to('mL/minute'))
                                y_r[n+1][2*i+1]=(run.set_total_flow_rate.to('mL/minute'))
                        elif reagent.gas_concentration_in is not None:
                            y_r[n][i]=(reagent.gas_concentration_in)
                            y_r_text="gas concentrations"
                        if i == len(self.section_runs)-1:
                            # y_r[n].append(y_r[n][i])
                            figR.add_trace(go.Scatter(x=x, y=y_r[n], name=reagent.name))
                            if n == len(run.reagents)-1:
                                figR.add_trace(go.Scatter(x=x, y=y_r[n+1], name='Total Flow Rates'))
            figT.add_trace(go.Scatter(x=x, y=y, name='Temperature'))
            figT.update_layout(title_text="Temperature")
            figT.update_xaxes(title_text=x_text)
            figT.update_yaxes(title_text="Temperature (K)")
            self.figures.append(PlotlyFigure(label='Temperature', figure=figT.to_plotly_json()))

            try:
                if figP is not None:
                    figP.add_trace(go.Scatter(x=x, y=y_p, name='Pressure'))
                    figP.update_layout(title_text="Pressure")
                    figP.update_xaxes(title_text=x_text,)
                    figP.update_yaxes(title_text="pressure (bar)")
                    self.figures.append(PlotlyFigure(label='Pressure', figure=figP.to_plotly_json()))
            except:
                pass
            try:
                if figR is not None:
                    figR.update_layout(title_text="Gas feed", showlegend=True)
                    figR.update_xaxes(title_text=x_text)
                    figR.update_yaxes(title_text=y_r_text)
                    self.figures.append(PlotlyFigure(label='Feed Gas', figure=figR.to_plotly_json()))
            except:
                pass
