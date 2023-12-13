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

from nomad.datamodel.metainfo.basesections import PubChemPureSubstanceSection

from nomad.metainfo import (
    Quantity,
    Section,
    SubSection,
)
from nomad.units import ureg

from nomad.datamodel.data import (
    ArchiveSection
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.results import (
    Results,
    Properties,
    CatalyticProperties,
    Reactivity
)
from nomad.datamodel.metainfo.plot import (
    PlotSection,
    PlotlyFigure,
)

def add_activity(archive):
    '''Adds metainfo structure for catalysis activity test data.'''
    if not archive.results:
        archive.results = Results()
    if not archive.results.properties:
        archive.results.properties = Properties()
    if not archive.results.properties.catalytic:
        archive.results.properties.catalytic = CatalyticProperties()
    if not archive.results.properties.catalytic.reactivity:
        archive.results.properties.catalytic.reactivity = Reactivity()

class Reagent(ArchiveSection):
    m_def = Section(label_quantity='name', description='a chemical substance present in the initial reaction mixture')
    name = Quantity(type=str, a_eln=ELNAnnotation(label='reagent name', component='StringEditQuantity'), description="reagent name")
    gas_concentration_in = Quantity(
        type=np.float64, shape=['*'],
        description='Volumetric fraction of reactant in feed gas.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'))
    flow_rate = Quantity(
        type=np.float64, shape=['*'], unit='mL/minute',
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

        if self.name is None and self.pure_reagent is not None:
            self.name = self.pure_reagent.molecular_formula


class ReactionConditions(PlotSection, ArchiveSection):
    m_def = Section(description='A class containing reaction conditions for a generic reaction.')

    set_temperature = Quantity(
        type=np.float64, shape=['*'], unit='K', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    set_pressure = Quantity(
        type=np.float64, shape=['*'], unit='bar', a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='bar'))

    set_total_flow_rate = Quantity(
        type=np.float64, shape=['*'], unit='mL/minute', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    weight_hourly_space_velocity = Quantity(
        type=np.float64, shape=['*'], unit='mL/(g*hour)', a_eln=dict(component='NumberEditQuantity'))

    contact_time = Quantity(
        type=np.float64, shape=['*'], unit='g*s/mL', a_eln=ELNAnnotation(label='W|F'))

    gas_hourly_space_velocity = Quantity(
        type=np.float64, shape=['*'], unit='1/hour', a_eln=dict(component='NumberEditQuantity'))

    runs = Quantity(type=np.float64, shape=['*'])

    sampling_frequency = Quantity(
        type=np.float64, shape=[], unit='Hz',
        description='The number of measurement points per time.',
        a_eln=dict(component='NumberEditQuantity'))

    time_on_stream = Quantity(
        type=np.float64, shape=['*'], unit='hour', a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='hour'))

    reagents = SubSection(section_def=Reagent, repeats=True)

    def normalize(self, archive, logger):
        super(ReactionConditions, self).normalize(archive, logger)
        for reagent in self.reagents:
            reagent.normalize(archive, logger)

        if self.runs is None and self.set_temperature is not None:
            number_of_runs=len(self.set_temperature)
            self.runs= np.linspace(0, number_of_runs - 1, number_of_runs)
        else:
            number_of_runs=len(self.runs)

        if self.set_pressure is not None:
            if len(self.set_pressure) == 1:
                for n in range(number_of_runs-1):
                    self.set_pressure=np.append(self.set_pressure, self.set_pressure[0])

        if self.set_total_flow_rate is None and self.reagents is not None:
            self.set_total_flow_rate = np.array([])
            for n in range(number_of_runs):
                total_flow_rate=0
                for reagent in self.reagents:
                    if reagent.flow_rate is not None:
                        if len(reagent.flow_rate) == 1:
                            for m in range(number_of_runs-1):
                                reagent.flow_rate=np.append(reagent.flow_rate, reagent.flow_rate[0])
                        elif len(reagent.flow_rate) != number_of_runs:
                            raise ValueError('The number of flow rates is not equal to the number of runs')
                        total_flow_rate+=reagent.flow_rate[n]
                self.set_total_flow_rate=np.append(self.set_total_flow_rate, total_flow_rate)

        if self.set_total_flow_rate is not None:
            if len(self.set_total_flow_rate) == 1:
                set_total_flow_rate=[]
                for n in range(number_of_runs):
                    set_total_flow_rate.append(self.set_total_flow_rate)
                self.set_total_flow_rate=set_total_flow_rate

        for reagent in self.reagents:
            if reagent.gas_concentration_in is not None:
                if len(reagent.gas_concentration_in) == 1:
                    gas_concentration_in=[]
                    for n in range(number_of_runs):
                        gas_concentration_in.append(reagent.gas_concentration_in)
                    reagent.gas_concentration_in=gas_concentration_in
                elif len(reagent.gas_concentration_in) != number_of_runs:
                    raise ValueError('The number of gas concentrations is not equal to the number of runs')
            if reagent.flow_rate is not None:
                if len(reagent.flow_rate) == 1:
                    for n in range(number_of_runs):
                        print(type(reagent.flow_rate), reagent.flow_rate)
                        print(reagent.flow_rate[0])
                        reagent.flow_rate.append(reagent.flow_rate[0])
                elif len(reagent.flow_rate) != number_of_runs:
                    raise ValueError('The number of flow rates is not equal to the number of runs')

        add_activity(archive)

        if self.set_temperature is not None:
            archive.results.properties.catalytic.reactivity.test_temperatures = self.set_temperature
        if self.set_pressure is not None:
            archive.results.properties.catalytic.reactivity.pressure = self.set_pressure
        if self.set_total_flow_rate is not None:
            archive.results.properties.catalytic.reactivity.flow_rate = self.set_total_flow_rate
        if self.weight_hourly_space_velocity is not None:
            archive.results.properties.catalytic.reactivity.weight_hourly_space_velocity = self.weight_hourly_space_velocity
        if self.reagents is not None:
            archive.results.properties.catalytic.reactivity.reactants = self.reagents

        #Figures definitions:
        if self.time_on_stream is not None:
            x=self.time_on_stream.to('hour')
            x_text="time (h)"
        else:
            x=self.runs
            x_text="steps"

        if self.set_temperature is not None:
            figT = px.scatter(x=x, y=self.set_temperature.to('kelvin'))
            figT.update_layout(title_text="Temperature")
            figT.update_xaxes(title_text=x_text,)
            figT.update_yaxes(title_text="Temperature (K)")
            self.figures.append(PlotlyFigure(label='Temperature', figure=figT.to_plotly_json()))

        if self.set_pressure is not None:
            figP = px.scatter(x=x, y=self.set_pressure.to('bar'))
            figP.update_layout(title_text="Pressure")
            figP.update_xaxes(title_text=x_text,)
            figP.update_yaxes(title_text="pressure (bar)")
            self.figures.append(PlotlyFigure(label='Pressure', figure=figP.to_plotly_json()))

        if self.reagents is not None and (self.reagents[0].flow_rate is not None or self.reagents[0].gas_concentration_in is not None):
            fig5 = go.Figure()
            for i,r in enumerate(self.reagents):
                if r.flow_rate is not None:
                    y=r.flow_rate.to('mL/minute')
                    fig5.add_trace(go.Scatter(x=x, y=y, name=r.name))
                    y5_text="Flow rates (mL/min)"
                    if self.set_total_flow_rate is not None and i == 0:
                        fig5.add_trace(go.Scatter(x=x,y=self.set_total_flow_rate, name='Total Flow Rates'))
                elif self.reagents[0].gas_concentration_in is not None:
                    fig5.add_trace(go.Scatter(x=x, y=self.reagents[i].gas_concentration_in, name=self.reagents[i].name))    
                    y5_text="gas concentrations"
            fig5.update_layout(title_text="Gas feed", showlegend=True)
            fig5.update_xaxes(title_text=x_text)
            fig5.update_yaxes(title_text=y5_text)
            self.figures.append(PlotlyFigure(label='Feed Gas', figure=fig5.to_plotly_json()))
