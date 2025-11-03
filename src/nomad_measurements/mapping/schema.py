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

from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    Measurement,
    MeasurementResult,
)
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package()


class MappingResult(MeasurementResult):
    """A class representing the result of a mapping measurement."""

    m_def = Section()
    x_relative = Quantity(
        type=np.float64,
        description="""
        The x position of the measurement relative to the center of mass of the whole
        sample.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_relative = Quantity(
        type=np.float64,
        description="""
        The y position of the measurement relative to the center of mass of the whole
        sample.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    x_absolute = Quantity(
        type=np.float64,
        description="""
        The absolute x position of the measurement in the coordinate system of the
        measurement stage.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_absolute = Quantity(
        type=np.float64,
        description="""
        The absolute y position of the measurement in the coordinate system of the
        measurement stage.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `MappingResult` class.
        Will set the name of the section to the relative position of the measurement in
        mm. If the relative position is not available, the absolute position will be
        used.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if isinstance(self.x_relative, ureg.Quantity) and isinstance(
            self.y_relative, ureg.Quantity
        ):
            self.name = (
                f'Sample x = {self.x_relative.to("mm").magnitude:.1f} mm, '
                f'y = {self.y_relative.to("mm").magnitude:.1f} mm'
            )
        elif isinstance(self.x_absolute, ureg.Quantity) and isinstance(
            self.y_absolute, ureg.Quantity
        ):
            self.name = (
                f'Stage x = {self.x_absolute.to("mm").magnitude:.1f} mm, '
                f'y = {self.y_absolute.to("mm").magnitude:.1f} mm'
            )


class AffineTransformation(ArchiveSection):
    m_def = Section()
    v1_before = Quantity(
        type=np.float64,
        unit='m',
        description='The v1 vector of the sample before the transformation.',
        shape=[2],
    )
    v2_before = Quantity(
        type=np.float64,
        unit='m',
        description='The v2 vector of the sample before the transformation.',
        shape=[2],
    )
    v3_before = Quantity(
        type=np.float64,
        unit='m',
        description='The v3 vector of the sample before the transformation.',
        shape=[2],
    )
    v1_after = Quantity(
        type=np.float64,
        unit='m',
        description='The v1 vector of the sample after the transformation.',
        shape=[2],
    )
    v2_after = Quantity(
        type=np.float64,
        unit='m',
        description='The v2 vector of the sample after the transformation.',
        shape=[2],
    )
    v3_after = Quantity(
        type=np.float64,
        unit='m',
        description='The v3 vector of the sample after the transformation.',
        shape=[2],
    )
    transformation_matrix = Quantity(
        type=np.float64,
        description='The transformation matrix.',
        shape=[2, 2],
    )
    translation_vector = Quantity(
        type=np.float64,
        unit='m',
        description='The translation vector.',
        shape=[2],
    )

    def calculate_affine_transformation(self) -> None:
        """
        Calculate the affine transformation matrix and translation vector from the
        sample alignment.
        """
        if (
            not isinstance(self.v1_before, ureg.Quantity)
            or not isinstance(self.v2_before, ureg.Quantity)
            or not isinstance(self.v3_before, ureg.Quantity)
            or not isinstance(self.v1_after, ureg.Quantity)
            or not isinstance(self.v2_after, ureg.Quantity)
            or not isinstance(self.v3_after, ureg.Quantity)
        ):
            return
        # Construct the matrix A and vector b for the system of equations

        a_matrix = np.array(
            [
                [
                    self.v1_before[0].to('m').magnitude,
                    self.v1_before[1].to('m').magnitude,
                    1,
                    0,
                    0,
                    0,
                ],
                [
                    0,
                    0,
                    0,
                    self.v1_before[0].to('m').magnitude,
                    self.v1_before[1].to('m').magnitude,
                    1,
                ],
                [
                    self.v2_before[0].to('m').magnitude,
                    self.v2_before[1].to('m').magnitude,
                    1,
                    0,
                    0,
                    0,
                ],
                [
                    0,
                    0,
                    0,
                    self.v2_before[0].to('m').magnitude,
                    self.v2_before[1].to('m').magnitude,
                    1,
                ],
                [
                    self.v3_before[0].to('m').magnitude,
                    self.v3_before[1].to('m').magnitude,
                    1,
                    0,
                    0,
                    0,
                ],
                [
                    0,
                    0,
                    0,
                    self.v3_before[0].to('m').magnitude,
                    self.v3_before[1].to('m').magnitude,
                    1,
                ],
            ]
        )

        b_vector = np.array(
            [
                self.v1_after[0].to('m').magnitude,
                self.v1_after[1].to('m').magnitude,
                self.v2_after[0].to('m').magnitude,
                self.v2_after[1].to('m').magnitude,
                self.v3_after[0].to('m').magnitude,
                self.v3_after[1].to('m').magnitude,
            ]
        )

        # Solve for the transformation parameters
        params = np.linalg.solve(a_matrix, b_vector)

        # Extract the transformation matrix and translation vector
        self.transformation_matrix = np.array(
            [[params[0], params[1]], [params[3], params[4]]]
        )

        self.translation_vector = np.array([params[2], params[5]])

    def transform_vector(self, vector: np.ndarray) -> np.ndarray:
        """
        Apply the affine transformation to a vector.

        Args:
            vector (np.ndarray): The vector before the transformation.

        Returns:
            np.ndarray: The vector after the transformation.
        """
        if self.transformation_matrix is None or self.translation_vector is None:
            return None, None
        return (
            self.transformation_matrix @ vector * ureg.meter + self.translation_vector
        )


class SampleAlignment(ArchiveSection):
    """A class representing the alignment of a sample."""

    m_def = Section()
    affine_transformation = SubSection(
        section_def=AffineTransformation,
        description='The affine transformation of the sample.',
    )


class RectangularSampleAlignment(SampleAlignment):
    """A class representing the alignment of a rectangular sample."""

    m_def = Section()
    width = Quantity(
        type=np.float64,
        description='The width of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    height = Quantity(
        type=np.float64,
        description='The height of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    x_upper_left = Quantity(
        type=np.float64,
        description='The x position of the upper left corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_upper_left = Quantity(
        type=np.float64,
        description='The y position of the upper left corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    x_lower_right = Quantity(
        type=np.float64,
        description='The x position of the lower right corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_lower_right = Quantity(
        type=np.float64,
        description='The y position of the lower right corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )

    @staticmethod
    def calculate_lower_left(
        a: np.ndarray, b: np.ndarray, h: float, w: float
    ) -> tuple[float, float]:
        """
        Calculate the coordinates of the lower left corner of a rectangle.

        Args:
            a (np.ndarray): The coordinates of the upper left corner.
            b (np.ndarray): The coordinates of point B.
            h (float): The height of the rectangle.
            w (float): The width of the rectangle.

        Returns:
            tuple[float, float]: The coordinates of the lower left corner.
        """
        ab = b - a
        d = np.linalg.norm(ab)
        dy = h * (ab[0] * w - ab[1] * h) / d**2
        dx = h * (ab[1] * w + ab[0] * h) / d**2
        return (a[0] + dx, a[1] - dy)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RectangularSampleAlignment` class.
        Will calculate the affine transformation from the sample alignment.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if (
            isinstance(self.width, ureg.Quantity)
            and isinstance(self.height, ureg.Quantity)
            and isinstance(self.x_upper_left, ureg.Quantity)
            and isinstance(self.y_upper_left, ureg.Quantity)
            and isinstance(self.x_lower_right, ureg.Quantity)
            and isinstance(self.y_lower_right, ureg.Quantity)
        ):
            x0 = self.x_upper_left.to('m').magnitude
            y0 = self.y_upper_left.to('m').magnitude
            x1 = self.x_lower_right.to('m').magnitude
            y1 = self.y_lower_right.to('m').magnitude
            h = self.height.to('m').magnitude
            w = self.width.to('m').magnitude
            x2, y2 = self.calculate_lower_left(
                np.array([x0, y0]), np.array([x1, y1]), h, w
            )
            t = AffineTransformation(
                v1_before=[x0, y0],
                v2_before=[x2, y2],
                v3_before=[x1, y1],
                v1_after=[-w / 2, h / 2],
                v2_after=[-w / 2, -h / 2],
                v3_after=[w / 2, -h / 2],
            )
            t.calculate_affine_transformation()
            self.affine_transformation = t

        super().normalize(archive, logger)


class MappingMeasurement(Measurement):
    """A class representing a mapping measurement."""

    m_def = Section()
    sample_alignment = SubSection(
        section_def=SampleAlignment,
        description='The alignment of the sample.',
    )
    results = SubSection(
        section_def=MappingResult,
        repeats=True,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `MappingMeasurement` class.
        Will normalize the sample alignment and the mapping results.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        result: MappingResult
        for result in self.results:
            if (
                not isinstance(self.sample_alignment, SampleAlignment)
                or not isinstance(result.y_absolute, ureg.Quantity)
                or not isinstance(result.x_absolute, ureg.Quantity)
                or not isinstance(
                    self.sample_alignment.affine_transformation,
                    AffineTransformation,
                )
            ):
                continue
            x, y = self.sample_alignment.affine_transformation.transform_vector(
                np.array(
                    [
                        result.x_absolute.to('m').magnitude,
                        result.y_absolute.to('m').magnitude,
                    ]
                )
            )
            result.x_relative = x
            result.y_relative = y
            result.normalize(archive, logger)


m_package.__init_metainfo__()
