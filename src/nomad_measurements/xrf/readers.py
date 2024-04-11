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

    # Splitting data into individual measurements
    measurements = re.split(r'_{100,}\n', data)
    for measurement in measurements:
        if len(measurement) > 100:
            # Try to match meta information
            meta_match = re.search(
                r'PositionType\s+Application\s+Sample name\s+Date\s+(\S+)\s+Quant analysis\s+(\S+(?:\s\S+)*)\s+(\S+)\s+(\d{4}-\s*\d{1,2}-\s*\d{1,2}\s+\d{1,2}:\d{2})',
                measurement,
            )

            # Try to match elements and their shares
            elements_match = re.search(
                r'Component\s+Film1\s+(.*?)\s+Analyzed value', measurement, re.DOTALL
            )
            shares_match = re.search(
                r'Analyzed\s+value\s+(.*?)\s+Unit', measurement, re.DOTALL
            )
            units_match = re.search(r'Unit\s+(.*?)\s+Component', measurement, re.DOTALL)

            if not (meta_match and elements_match and shares_match and units_match):
                logger.warn(
                    f'read_UBIK_txt failed to extract all necessary information from file: "{file_path}"'
                )
                continue

            else:
                # Extract metadata
                position = meta_match.group(1).strip()
                application = meta_match.group(2).strip()
                sample_name = meta_match.group(3).strip()
                # workaround for missing zeros, e.g. '2024- 3- 3  9:33' -> '2024- 3- 3 T9:33' -> '2024-3-3T9:33'
                date = 'T'.join(meta_match.group(4).strip().rsplit(' ', 1))
                date = datetime.strptime(date.replace(' ', ''), '%Y-%m-%dT%H:%M')

                # Extract elements and shares
                elements = elements_match.group(1).split()
                shares = shares_match.group(1).split()
                units = units_match.group(1).split()

                # Initialize dictionary for each measurement
                if application not in xrf_dict:
                    xrf_dict[application] = dict()
                    xrf_dict[application]['position'] = position
                    xrf_dict[application]['application'] = application
                    xrf_dict[application]['sample_name'] = sample_name
                    xrf_dict[application]['date'] = date
                    xrf_dict[application]['film_thickness'] = shares[0]
                    xrf_dict[application]['elements'] = dict()

                    for el, val, unit in zip(elements, shares[1:], units[1:]):
                        xrf_dict[application]['elements'][el] = dict()
                        xrf_dict[application]['elements'][el]['element'] = el
                        if unit == 'mass%':
                            xrf_dict[application]['elements'][el][
                                'mass_fraction'
                            ] = float(val)
                        elif unit == 'at%':
                            xrf_dict[application]['elements'][el][
                                'atomic_fraction'
                            ] = float(val)
                        else:
                            logger.warn(
                                f'read_UBIK_txt found unknown unit "{unit}" in file: "{file_path}"'
                            )
                else:
                    logger.warn(
                        f'read_UBIK_txt found duplicate application "{application}" in file: "{file_path}".'
                    )

    return xrf_dict
