import numpy as np

from nomad.datamodel.metainfo.basesections import (
    Component,
    CompositeSystem,
    PureSubstanceComponent,
    PureSubstanceSection,
)
from nomad.units import ureg
from nomad_measurements.utils import(
    merge_sections,
    to_pint_quantity,
)

def test_merge_sections():
    component_1 = Component(
        mass_fraction=1,
    )
    component_2 = Component(
        name='Cu',
        mass_fraction=1,
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
    assert system_1.components[0].mass_fraction == 1
    assert system_1.components[0].name == 'Cu'
    assert system_1.components[1].name == 'Cu'
    assert system_1.components[1].pure_substance.name == 'Cu'
    assert system_1.components[1].pure_substance.iupac_name == 'Copper'
    assert system_1.components[2].name == 'Fe'
    merge_sections(system_3, system_2)
    assert system_3.components[0].name == 'Cu'

def test_to_pint_quantity():
    assert to_pint_quantity(None, None) is None
    assert to_pint_quantity(None, 'mA') is None
    assert to_pint_quantity('Copper', '') == 'Copper'
    assert to_pint_quantity('Copper', 'mA') == 'Copper'
    assert to_pint_quantity(3., '') == 3 * ureg.dimensionless
    assert to_pint_quantity(3. * ureg.m, None) == 3 * ureg.m
    assert to_pint_quantity(3. * ureg.m, 'cm') == 300 * ureg.cm
    assert to_pint_quantity(1, None) == 1
    assert (to_pint_quantity(np.asarray([1., 2.]), 'm') \
        == np.asarray([1., 2.]) * ureg.m).all()
    assert (to_pint_quantity(np.asarray([1., 2.]), '') \
        == np.asarray([1., 2.]) * ureg.dimensionless).all()
    assert to_pint_quantity(1, 'mA') == 1 * ureg.mA

if __name__ == '__main__':
    test_merge_sections()
