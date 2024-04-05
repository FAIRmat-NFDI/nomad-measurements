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

if TYPE_CHECKING:
    from structlog.stdlib import (
        BoundLogger,
    )

def read_UBIK_txt(file_path: str, logger: 'BoundLogger' = None) -> Dict[str, Any]:
    """
    Function for reading the X-ray fluorescence data in a UBIK `.trn` file.

    Args:
        file_path (str): The path to the `.trn` file.
        logger (BoundLogger): A structlog logger.

    Returns:
        Dict[str, Any]: The X-ray fluorescence data in a Python dictionary.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    xrf_dict = dict(
        film_thickness = None
    )

    for line in lines:
        if 'Analyzed value' in line:
            xrf_dict['film_thickness'] = float(line.split()[2])
            break

    return xrf_dict
