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

    xrf_dict = dict(
        application = None,
        sample_name = None,
        date = None,
        film_thickness = None,
        elements = dict(),
    )

    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read()

    # Splitting data into individual measurements
    measurements = re.split(r'_{100,}\n', data)
    for measurement in measurements:
        if len(measurement) > 100:

            # Extract meta information
            meta_match = re.search(r'PositionType\s+Application\s+Sample name\s+Date\s+A-\d+\s+Quant analysis\s+(\S+)\s+on\s+(\S+)\s+(\S+)\s+(\d{4}-\s*\d{1,2}-\s*\d{1,2}\s+\d{1,2}:\d{2})', measurement)
            if meta_match:
                xrf_dict['application'] = meta_match.group(1).strip()
                xrf_dict['sample_name'] = meta_match.group(3).strip()
                # workaround for missing zeros, e.g. '2024- 3- 3  9:33' -> '2024- 3- 3T9:33' -> '2024-3-3T9:33'
                date = 'T'.join(meta_match.group(4).strip().rsplit(' ',1))
                xrf_dict['date'] = datetime.strptime(date.replace(' ',''), '%Y-%m-%dT%H:%M')

            # Extract elements and their shares
            elements_match = re.search(r'Component\s+Film1\s+(.*?)\s+Analyzed value', measurement, re.DOTALL)
            shares_match = re.search(r'Analyzed\s+value\s+(.*?)\s+Unit', measurement, re.DOTALL)
            units_match = re.search(r'Unit\s+(.*?)\s+Component', measurement, re.DOTALL)

            if elements_match and shares_match and units_match:
                elements = elements_match.group(1).split()
                shares = shares_match.group(1).split()
                units = units_match.group(1).split()

                xrf_dict['film_thickness'] = shares[0]

                for el,sh,un in zip(elements, shares[1:], units[1:]):
                    xrf_dict['elements'][el] = sh

    return xrf_dict
