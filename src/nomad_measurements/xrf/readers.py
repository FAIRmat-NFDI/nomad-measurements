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

    def group_composition_into_layers(
        layers: dict = {},
        names: list = [],
        values: list = [],
        units: list = [],
    ) -> dict:
        """
        Function for grouping the composition data into layers.

        Args:
            layers (dict): The layers to group the data into.
            names (list): The names of the layers.
            values (list): The values of the layers.
            units (list): The units of the layers.

        Returns:
            dict: The data grouped into layers.
        """
        reached_metal_layer = False
        reached_substrate_layer = False

        for name, value, unit in zip(names, values, units):
            if '%' not in unit:
                current_layer = name
                layers[current_layer] = dict()
                layers[current_layer]['thickness'] = value * ureg(unit)
                if 'layer' in current_layer.lower():
                    reached_metal_layer = True
            else:
                if reached_metal_layer and not reached_substrate_layer:
                    if name not in current_layer:
                        reached_substrate_layer = True
                        current_layer = 'Substrate'
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

    def sort_intensity_values_into_layers(
        layers: dict = {},
        int_peak_elements: list = [],
        int_peak_lines: list = [],
        int_peak_values: list = [],
        int_background_lines: list = [],
        int_background_types: list = [],
        int_background_values: list = [],
    ) -> dict:
        """
        Function for sorting the intensity values into layers.

        Args:
            layers (dict): The layers to sort the data into.
            int_peak_elements (list): The elements of the peak intensity values.
            int_peak_lines (list): The lines of the peak intensity values.
            int_peak_values (list): The values of the peak intensity values.
            int_background_lines (list): The lines of the background intensity values.
            int_background_types (list): The types of the background intensity values.
            int_background_values (list): The values of the background intensity values.

        Returns:
            dict: Updated dictionary with the intensity values sorted into layers.
        """
        int_dict = dict()

        # Group peak intensity values into dictionary
        for line, el, peak in zip(int_peak_lines, int_peak_elements, int_peak_values):
            if line not in int_dict:
                int_dict[line] = dict()
            int_dict[line]['element'] = el
            int_dict[line]['peak'] = peak

        # Group background intensity values into dictionary
        for line, bg_type, bg in zip(
            int_background_lines, int_background_types, int_background_values
        ):
            if bg_type == 'BG1':
                int_dict[line]['BG1'] = bg
            elif bg_type == 'BG2':
                int_dict[line]['BG2'] = bg

        # Sort intensity values into layers
        for layer in layers.values():
            for element, content in layer['elements'].items():
                for line, int_values in int_dict.items():
                    if element in line:
                        content['line'] = line
                        content['intensity_peak'] = int_values.get('peak')
                        content['intensity_background'] = int_values.get('BG1')
                        content['intensity_background_2'] = int_values.get('BG2')

        return layers

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

            # Try to match peak intensity values
            int_peak_elements_match = re.findall(
                r'Component\s+(.*?)\s+Element line', measurement
            )
            int_peak_lines_match = re.findall(
                r'Element line\s+(.*?)\s+Peak intensity', measurement
            )
            int_peak_values_match = re.findall(
                r'Peak intensity\s+(.*?)\s+BG intensity', measurement
            )

            # Try to match background intensity values
            int_background_lines_match = re.findall(
                r'Element line\s+(.*?)\s+Peak/BG', measurement
            )
            int_background_types_match = re.findall(
                r'Peak/BG\s+(.*?)\s+Meas. intensity', measurement
            )
            int_background_values_match = re.findall(
                r'Meas. intensity\s+(.*?)\n', measurement
            )

            # Check if all necessary information was found
            if all(
                (
                    meta_match,
                    names_match,
                    values_match,
                    units_match,
                    int_peak_elements_match,
                    int_peak_lines_match,
                    int_peak_values_match,
                    int_background_lines_match,
                    int_background_types_match,
                    int_background_values_match,
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
                values = [
                    float(value) for line in values_match for value in line.split()
                ]
                units = [unit for line in units_match for unit in line.split()]

                # Extract intensity values
                int_peak_elements = [
                    element
                    for line in int_peak_elements_match
                    for element in line.split()
                ]
                int_peak_lines = [
                    element for line in int_peak_lines_match for element in line.split()
                ]
                int_peak_values = [
                    float(element)
                    for line in int_peak_values_match
                    for element in line.split()
                ]
                int_background_lines = [
                    element
                    for line in int_background_lines_match
                    for element in line.split()
                ]
                int_background_types = [
                    element
                    for line in int_background_types_match
                    for element in line.split()
                ]
                int_background_values = [
                    float(element)
                    for line in int_background_values_match
                    for element in line.split()
                ]

                # Check if all intensity values have the same length
                if not all(
                    (
                        len(int_peak_elements)
                        == len(int_peak_lines)
                        == len(int_peak_values),
                        len(int_background_lines)
                        == len(int_background_types)
                        == len(int_background_values),
                    )
                ):
                    if logger is not None:
                        logger.warn(
                            f'read_UBIK_txt found inconsistent number of intensity values in file: "{file_path}"'
                        )

                # Check if application is not already in dictionary
                if application not in xrf_dict:
                    # Group data into layers
                    layers = {}
                    layers = group_composition_into_layers(layers, names, values, units)
                    layers = sort_intensity_values_into_layers(
                        layers,
                        int_peak_elements,
                        int_peak_lines,
                        int_peak_values,
                        int_background_lines,
                        int_background_types,
                        int_background_values,
                    )

                    # Fill dictionary with data
                    xrf_dict[application] = dict()
                    xrf_dict[application]['application'] = application
                    xrf_dict[application]['sample_name'] = sample_name
                    xrf_dict[application]['date'] = date
                    xrf_dict[application]['layers'] = layers
                else:
                    if logger is not None:
                        logger.warn(
                            f'read_UBIK_txt found duplicate application "{application}" in file: "{file_path}".'
                        )
            else:
                if logger is not None:
                    logger.warn(
                        f'read_UBIK_txt failed to extract all necessary information from file: "{file_path}"'
                    )

    # Delete layers with thickness 0
    for application in xrf_dict.values():
        layers_to_delete = []
        for layer_key, layer in application['layers'].items():
            try:
                if layer['thickness'] == 0:
                    layers_to_delete.append(layer_key)
            except KeyError:
                pass
        for key in layers_to_delete:
            del application['layers'][key]

    return xrf_dict
