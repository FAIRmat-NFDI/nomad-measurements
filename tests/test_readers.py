# #
# # Copyright The NOMAD Authors.
# #
# # This file is part of NOMAD. See https://nomad-lab.eu for further info.
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #     http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.
# #
# import json
# import numpy as np

# from nomad.units import ureg
# from pynxtools_xrd.read_file_formats import (
#     read_panalytical_xrdml,
#     read_rigaku_rasx,
#     read_bruker_brml,
# )


# def convert_quantity_to_string(data_dict):
#     """
#     In a dict, recursively convert every pint.Quantity into str containing its shape.

#     Args:
#         data_dict (dict): A nested dictionary containing pint.Quantity and other data.
#     """
#     for k, v in data_dict.items():
#         if isinstance(v, ureg.Quantity):
#             if isinstance(v.magnitude, np.ndarray):
#                 data_dict[k] = str(v.shape)
#             else:
#                 data_dict[k] = str(v.magnitude)
#         if isinstance(v, dict):
#             convert_quantity_to_string(v)


# def test_rasx_reader():
#     file_path = [
#         'tests/data/RSM_111_sdd=350.rasx',
#         'tests/data/Omega-2Theta_scan_high_temperature.rasx',
#     ]
#     for path in file_path:
#         output = read_rigaku_rasx(path)
#         convert_quantity_to_string(output)
#         with open(f'{path}.json', 'r', encoding='utf-8') as f:
#             reference = json.load(f)
#         assert output == reference


# def test_xrdml_reader():
#     file_path = [
#         'tests/data/XRD-918-16_10.xrdml',
#         'tests/data/m82762_rc1mm_1_16dg_src_slit_phi-101_3dg_-420_mesh_long.xrdml',
#     ]
#     for path in file_path:
#         output = read_panalytical_xrdml(path)
#         convert_quantity_to_string(output)
#         with open(f'{path}.json', 'r', encoding='utf-8') as f:
#             reference = json.load(f)
#         assert output == reference


# def test_brml_reader():
#     file_path = [
#         'tests/data/23-012-AG_2thomegascan_long.brml',
#         'tests/data/EJZ060_13_004_RSM.brml',
#     ]
#     for path in file_path:
#         output = read_bruker_brml(path)
#         convert_quantity_to_string(output)
#         with open(f'{path}.json', 'r', encoding='utf-8') as f:
#             reference = json.load(f)
#         assert output == reference
