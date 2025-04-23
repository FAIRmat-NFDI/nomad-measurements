#
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


from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
)
from nomad.datamodel.metainfo.basesections import ActivityStep
from nomad.metainfo import (
    MEnum,
    Quantity,
)


class QDMeasurementStep(ActivityStep):
    """
    A step in the QD measurement.
    """

    pass


class QDMeasurementSetTemperatureStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    temperature_set = Quantity(
        type=float,
        unit='kelvin',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='kelvin'
        ),
    )
    temperature_rate = Quantity(
        type=float,
        unit='kelvin/second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='kelvin/minute'
        ),
    )
    mode = Quantity(
        type=MEnum('Fast Settle', 'No Overshoot'),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )


class QDMeasurementSetMagneticFieldStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    field_set = Quantity(
        type=float,
        unit='gauss',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='gauss'),
    )
    field_rate = Quantity(
        type=float,
        unit='gauss/second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='gauss/second'
        ),
    )
    approach = Quantity(
        type=MEnum('Linear', 'No Overshoot', 'Oscillate'),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )
    end_mode = Quantity(
        type=MEnum('Persistent', 'Driven'),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )


class QDMeasurementWaitStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    delay = Quantity(
        type=float,
        unit='second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='second'
        ),
    )
    condition_temperature = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
    )
    condition_field = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
    )
    condition_position = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
    )
    condition_chamber = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
    )
    on_error_execute = Quantity(
        type=MEnum(
            'No Action',
            'Abort',
            'Shutdown',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )


class QDMeasurementScanFieldStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    initial_field = Quantity(
        type=float,
        unit='gauss',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='gauss'),
    )
    final_field = Quantity(
        type=float,
        unit='gauss',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='gauss'),
    )
    spacing_code = Quantity(
        type=MEnum(
            'Uniform',
            'H*H',
            'H^1/2',
            '1/H',
            'log(H)',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )
    # increments = Quantity(
    #    type=float,
    #    unit='tesla',
    #    a_eln=ELNAnnotation(
    #        component='NumberEditQuantity',
    #        defaultDisplayUnit='tesla'
    #    ),
    # )
    number_of_steps = Quantity(
        type=int,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
    )
    rate = Quantity(
        type=float,
        unit='gauss/second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='gauss/second'
        ),
    )
    approach = Quantity(
        type=MEnum(
            'Linear',
            'No Overshoot',
            'Oscillate',
            'Sweep',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )
    end_mode = Quantity(
        type=MEnum(
            'Persistent',
            'Driven',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )


class QDMeasurementScanFieldEndStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    pass


class QDMeasurementScanTempStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    initial_temp = Quantity(
        type=float,
        unit='kelvin',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='kelvin'
        ),
    )
    final_temp = Quantity(
        type=float,
        unit='kelvin',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='kelvin'
        ),
    )
    spacing_code = Quantity(
        type=MEnum(
            'Uniform',
            '1/T',
            'log(T)',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )
    number_of_steps = Quantity(
        type=int,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
    )
    rate = Quantity(
        type=float,
        unit='kelvin/second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='kelvin/minute'
        ),
    )
    approach = Quantity(
        type=MEnum(
            'Fast',
            'No Overshoot',
            'Sweep',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )


class QDMeasurementScanTempEndStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    pass


class QDMeasurementACTResistanceStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    measurement_active = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
        shape=[2],
    )
    excitation = Quantity(
        type=float,
        unit='ampere',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='milliampere'
        ),
        shape=[2],
    )
    frequency = Quantity(
        type=float,
        unit='hertz',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='hertz'),
        shape=[2],
    )
    duration = Quantity(
        type=float,
        unit='second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='second'
        ),
        shape=[2],
    )
    constant_current_mode = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
        shape=[2],
    )
    low_resistance_mode = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
        shape=[2],
    )
    autorange = Quantity(
        type=MEnum(
            'Always Autorange',
            'Sticky Autorange',
            'Fixed Gain',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
        shape=[2],
    )
    fixed_gain = Quantity(
        type=float,
        unit='volt',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='volt'),
        shape=[2],
    )


class QDMeasurementETOResistanceStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    mode = Quantity(
        type=MEnum(
            'Do Nothing',
            'Start Excitation',
            'Start Continuous Measure',
            'Perform N Measurements',
            'Stop Measurement',
            'Stop Excitation',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
        shape=[2],
    )
    excitation_amplitude = Quantity(
        # no unit, either milliAmpere for 4-wire or Volt for 2-wire
        type=float,
        a_eln=ELNAnnotation(
            component='NumberEditQuantity',
        ),
        shape=[2],
    )
    excitation_frequency = Quantity(
        type=float,
        unit='hertz',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='hertz'),
        shape=[2],
    )
    preamp_range = Quantity(
        # TODO: figure out to read this from sequence file (is in bins 9-11 somehow)
        # no unit, either Volt for 4-wire or Ampere for 2-wire
        type=float,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
        shape=[2],
    )
    preamp_sample_wiring = Quantity(
        type=MEnum(
            '4-wire',
            '2-wire',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
        shape=[2],
    )
    preamp_autorange = Quantity(
        type=bool,
        a_eln=ELNAnnotation(
            component='BoolEditQuantity',
        ),
        shape=[2],
    )
    config_averaging_time = Quantity(
        type=float,
        unit='second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='second'
        ),
        shape=[2],
    )
    config_number_of_measurements = Quantity(
        type=int,
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
        shape=[2],
    )


class QDMeasurementSetPositionStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    position_set = Quantity(
        type=float,
        unit='degree',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='degree'
        ),
    )
    position_rate = Quantity(
        type=float,
        unit='degree/second',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='degree/minute'
        ),
    )
    mode = Quantity(
        type=MEnum(
            'Move to position', 'Move to index and define', 'Redefine present position'
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )


class QDMeasurementRemarkStep(QDMeasurementStep):
    """
    A step in the QD measurement.
    """

    remark_text = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        ),
    )
