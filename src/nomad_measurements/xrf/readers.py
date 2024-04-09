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
# from nomad.units import ureg
import re
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

    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read()

    xrf_dict = dict()
    idx = 0

    # Splitting data into individual measurements
    measurements = re.split(r'_{100,}\n', data)
    for measurement in measurements:
        if len(measurement) > 100:
            # Initialize dictionary for each measurement
            key = str(idx)
            xrf_dict[key] = dict()
            idx += 1

            # Extract meta information
            meta_match = re.search(
                r'PositionType\s+Application\s+Sample name\s+Date\s+(\S+)\s+Quant analysis\s+(\S+(?:\s\S+)*)\s+(\S+)\s+(\d{4}-\s*\d{1,2}-\s*\d{1,2}\s+\d{1,2}:\d{2})',
                measurement,
            )
            if meta_match:
                xrf_dict[key]['position'] = meta_match.group(1).strip()
                xrf_dict[key]['application'] = meta_match.group(2).strip()
                xrf_dict[key]['sample_name'] = meta_match.group(3).strip()
                # workaround for missing zeros, e.g. '2024- 3- 3  9:33' -> '2024- 3- 3 T9:33' -> '2024-3-3T9:33'
                date = 'T'.join(meta_match.group(4).strip().rsplit(' ', 1))
                xrf_dict[key]['date'] = datetime.strptime(
                    date.replace(' ', ''), '%Y-%m-%dT%H:%M'
                )
            else:
                xrf_dict[key]['position'] = None
                xrf_dict[key]['application'] = None
                xrf_dict[key]['sample_name'] = None
                xrf_dict[key]['date'] = None
                logger.warn(
                    f'read_UBIK_txt failed to extract metadata from file: "{self.data_file}".'
                )

            # Extract elements and their shares
            elements_match = re.search(
                r'Component\s+Film1\s+(.*?)\s+Analyzed value', measurement, re.DOTALL
            )
            shares_match = re.search(
                r'Analyzed\s+value\s+(.*?)\s+Unit', measurement, re.DOTALL
            )
            units_match = re.search(r'Unit\s+(.*?)\s+Component', measurement, re.DOTALL)

            if elements_match and shares_match and units_match:
                elements = elements_match.group(1).split()
                shares = shares_match.group(1).split()
                units = units_match.group(1).split()

                xrf_dict[key]['film_thickness'] = shares[0]
                xrf_dict[key]['elements'] = dict()

                for el, sh, un in zip(elements, shares[1:], units[1:]):
                    xrf_dict[key]['elements'][el] = dict()
                    xrf_dict[key]['elements'][el]['value'] = float(sh)
                    xrf_dict[key]['elements'][el]['unit'] = un
            else:
                xrf_dict[key]['film_thickness'] = None
                xrf_dict[key]['elements'] = None
                logger.warn(
                    f'read_UBIK_txt failed to extract elements and shares from file: "{self.data_file}".'
                )

    return xrf_dict
