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
from nomad.datamodel.metainfo.basesections import (
    Component,
    CompositeSystem,
    PureSubstanceComponent,
    PureSubstanceSection,
)
from nomad.metainfo import MEnum, Quantity
from nomad.units import ureg

from nomad_measurements.utils import (
    merge_sections,
)


class TestComponent(Component):
    float_array = Quantity(type=np.float64, shape=[2, '*'])
    float_array_w_units = Quantity(type=np.float64, shape=['*'], unit='eV')
    float_array_w_diff_length = Quantity(type=np.float64, shape=['*'])
    bool_array = Quantity(type=bool, shape=['*'])
    enum_value = Quantity(type=MEnum(['A', 'B', 'C']))


def test_merge_sections(capfd):
    component_1 = TestComponent(
        mass_fraction=1,
        bool_array=[True, False],
        float_array=[[1.0, 1.0], [1.0, 3.0]],
        float_array_w_units=[1.0, 1.0],
        float_array_w_diff_length=[1.0, 3.0],
        enum_value='A',
    )
    component_2 = TestComponent(
        name='Cu',
        mass_fraction=1,
        bool_array=[True, True],
        float_array=[[1.0, 3.0], [1.0, 3.0]],
        float_array_w_units=[1.0, 1.0],
        float_array_w_diff_length=[1.0, 3.0, 4.0],
        enum_value='A',
    )
    substance_1 = PureSubstanceSection(
        name='Cu',
    )
    substance_2 = PureSubstanceSection(
        iupac_name='Copper',
    )
    component_3 = PureSubstanceComponent(
        name='Cu',
        pure_substance=substance_1,
    )
    component_4 = PureSubstanceComponent(
        name='Fe',
        pure_substance=substance_2,
    )
    component_5 = Component()
    component_6 = Component(
        name='Fe',
    )
    system_1 = CompositeSystem(
        components=[component_1, component_3, component_5],
    )
    system_2 = CompositeSystem(
        components=[component_2, component_4, component_6],
    )
    system_3 = CompositeSystem()
    merge_sections(system_1, system_2)
    out, _ = capfd.readouterr()
    assert out == (
        'Merging sections with different values for quantity "bool_array".\n'
        'Merging sections with different values for quantity "float_array".\n'
        'Merging sections with different values for quantity '
        '"float_array_w_diff_length".\n'
        'Merging sections with different values for quantity "name".\n'
    )
    assert system_1.components[0].mass_fraction == 1
    assert system_1.components[0].name == 'Cu'
    assert system_1.components[0].bool_array[0] is True
    assert system_1.components[0].bool_array[1] is False
    assert system_1.components[0].float_array[0][0] == 1.0
    assert system_1.components[0].float_array[0][1] == 1.0
    assert system_1.components[0].float_array_w_units[0] == ureg.Quantity(1.0, 'eV')
    assert system_1.components[0].float_array_w_units[1] == ureg.Quantity(1.0, 'eV')
    assert system_1.components[0].enum_value == 'A'
    assert system_1.components[1].name == 'Cu'
    assert system_1.components[1].pure_substance.name == 'Cu'
    assert system_1.components[1].pure_substance.iupac_name == 'Copper'
    assert system_1.components[2].name == 'Fe'
    merge_sections(system_3, system_2)
    assert system_3.components[0].name == 'Cu'


if __name__ == '__main__':
    test_merge_sections()
