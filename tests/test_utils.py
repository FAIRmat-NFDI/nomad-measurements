from nomad.datamodel.metainfo.basesections import (
    Component,
    CompositeSystem,
    PureSubstanceComponent,
    PureSubstanceSection,
)
from nomad_measurements.utils import merge_sections

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

if __name__ == '__main__':
    test_merge_sections()
