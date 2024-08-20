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

from nomad.config.models.plugins import ParserEntryPoint, SchemaPackageEntryPoint


class TransmissionSchemaPackageEntryPoint(SchemaPackageEntryPoint):

    def load(self):
        from nomad_measurements.transmission.schema import m_package

        return m_package


schema = TransmissionSchemaPackageEntryPoint(
    name='TransmissionSchema',
    description='Schema package defined using the new plugin mechanism.',
)


class TransmissionParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements.transmission.parser import TransmissionParser

        return TransmissionParser(**self.dict())


parser = TransmissionParserEntryPoint(
    name='Transmission Parser',
    description='Parser defined using the new plugin mechanism.',
    mainfile_name_re=r'^.*\.asc$',
)
