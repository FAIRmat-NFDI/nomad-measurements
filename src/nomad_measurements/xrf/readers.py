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

from typing import Dict, Any, TYPE_CHECKING

# import numpy as np
from nomad.units import ureg
import re
import itertools
from datetime import datetime

if TYPE_CHECKING:
    from structlog.stdlib import (
        BoundLogger,
    )


def read_UBIK_txt(file_path: str, logger: 'BoundLogger' = None) -> Dict[str, Any]:
    """
    Function for reading the X-ray fluorescence data in a UBIK `.txt` file.

    Args:
        file_path (str): The path to the `.txt` file.
        logger (BoundLogger): A structlog logger.

    Returns:
        Dict[str, Any]: The X-ray fluorescence data in a Python dictionary.
    """

    def group_composition_into_layers(names: list, values: list, units: list) -> dict:
        """
        Function for grouping the composition data into layers.

        Args:
            names (list): The names of the layers.
            values (list): The values of the layers.
            units (list): The units of the layers.

        Returns:
            dict: The data grouped into layers.
        """
        reached_metal_layer = False
        reached_substrate_layer = False
        layers = dict()
        for name, value, unit in zip(names, values, units):
            if '%' not in unit:
                current_layer = name
                layers[current_layer] = dict()
                layers[current_layer]['thickness'] = float(value) * ureg(unit)
                if 'layer' in current_layer.lower():
                    reached_metal_layer = True
            else:
                if reached_metal_layer and not reached_substrate_layer:
                    if name not in current_layer:
                        reached_substrate_layer = True
                        current_layer = 'substrate'
                        layers[current_layer] = dict()
                if not layers[current_layer].get('elements'):
                    layers[current_layer]['elements'] = dict()
                if unit == 'mass%':
                    layers[current_layer]['elements'][name] = dict(mass_fraction=value)
                elif unit == 'at%':
                    layers[current_layer]['elements'][name] = dict(
                        atomic_fraction=value
                    )
                else:
                    logger.warn(
                        f'read_UBIK_txt found unknown unit "{unit}" in file: "{file_path}"'
                    )
        return layers

    def group_intensity_values(
        component: list,
        element_line: list,
        peak: list,
        background: list,
    ) -> dict:
        """
        Function for grouping the intensity values into a dictionary.

        Args:
            component (list): The component values.
            element_line (list): The element line values.
            peak (list): The peak values.
            background (list): The background values.

        Returns:
            dict: The intensity values grouped into a dictionary.
        """
        intensity_values = dict()
        for comp, el, pk, bg in zip(component, element_line, peak, background):
            if comp not in intensity_values:
                intensity_values[comp] = dict()
            intensity_values[comp][el] = dict(peak=pk, background=bg)
        return intensity_values

    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read()

    xrf_dict = dict()

    # Splitting data into individual measurements
    measurements = re.split(r'_{100,}\n', data)
    for measurement in measurements:
        if len(measurement) > 100:
            # Try to match meta information
            meta_match = re.search(
                r'PositionType\s+Application\s+Sample name\s+Date\s+(\S+)\s+Quant analysis\s+(\S+(?:\s\S+)*)\s+(\S+)\s+(\d{4}-\s*\d{1,2}-\s*\d{1,2}\s+\d{1,2}:\d{2})',
                measurement,
            )

            # Try to match layers/elements and their thickness/shares
            names_match = re.findall(r'Component\s+(.*?)\s+Analyzed value', measurement)
            values_match = re.findall(r'Analyzed value\s+(.*?)\s+Unit', measurement)
            units_match = re.findall(r'Unit\s+(.*?)\s+Component', measurement)

            # Try to match intensity values
            intensity_component_match = re.findall(
                r'Component\s+(.*?)\s+Element line', measurement
            )
            intensity_element_line_match = re.findall(
                r'Element line\s+(.*?)\s+Peak intensity', measurement
            )
            intensity_peak_match = re.findall(
                r'Peak intensity\s+(.*?)\s+BG intensity', measurement
            )
            intensity_background_match = re.findall(
                r'BG intensity\s+(.*?)\s+Net intensity', measurement
            )

            # Check if all necessary information was found
            if all(
                (
                    meta_match,
                    names_match,
                    values_match,
                    units_match,
                    intensity_component_match,
                    intensity_element_line_match,
                    intensity_peak_match,
                    intensity_background_match,
                )
            ):
                # Extract metadata
                application = meta_match.group(2).strip()
                sample_name = meta_match.group(3).strip()
                # workaround for missing zeros, e.g. '2024- 3- 3  9:33' -> '2024- 3- 3 T9:33' -> '2024-3-3T9:33'
                date = 'T'.join(meta_match.group(4).strip().rsplit(' ', 1))
                date = datetime.strptime(date.replace(' ', ''), '%Y-%m-%dT%H:%M')

                # Extract elements and shares
                names = [name for line in names_match for name in line.split()]
                values = [value for line in values_match for value in line.split()]
                units = [unit for line in units_match for unit in line.split()]

                # Extract intensity values
                intensity_component = [
                    comp for line in intensity_component_match for comp in line.split()
                ]
                intensity_element_line = [
                    el for line in intensity_element_line_match for el in line.split()
                ]
                intensity_peak = [
                    pk for line in intensity_peak_match for pk in line.split()
                ]
                intensity_background = [
                    bg for line in intensity_background_match for bg in line.split()
                ]

                # Check if all intensity values have the same length
                if not all(
                    (
                        len(intensity_component) == len(intensity_element_line),
                        len(intensity_element_line) == len(intensity_peak),
                        len(intensity_peak) == len(intensity_background),
                    )
                ):
                    logger.warn(
                        f'read_UBIK_txt found inconsistent number of intensity values in file: "{file_path}"'
                    )
                    continue

                # Check if application is not already in dictionary
                if application not in xrf_dict:
                    # Group data into layers
                    layers = group_composition_into_layers(names, values, units)

                    # TODO: continue here!

                    # Fill dictionary with data
                    xrf_dict[application] = dict()
                    xrf_dict[application]['application'] = application
                    xrf_dict[application]['sample_name'] = sample_name
                    xrf_dict[application]['date'] = date
                    xrf_dict[application]['layers'] = layers
                else:
                    logger.warn(
                        f'read_UBIK_txt found duplicate application "{application}" in file: "{file_path}".'
                    )
            else:
                logger.warn(
                    f'read_UBIK_txt failed to extract all necessary information from file: "{file_path}"'
                )
                continue

    return xrf_dict
