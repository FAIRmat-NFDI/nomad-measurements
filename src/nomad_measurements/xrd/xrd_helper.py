"""
Gethering of functions and classes that are needed to calculate
some properties, features and to map data into nomad.
"""
import numpy as np


def calculate_two_theta_or_scattering_vector(q=None, two_theta=None, wavelength=None):
    """
    Calculate the two-theta array from the scattering vector (q) or vice-versa,
    given the wavelength of the X-ray source.

    Args:
        q (array-like, optional): Array of scattering vectors, in angstroms^-1.
        two_theta (array-like, optional): Array of two-theta angles, in degrees.
        wavelength (float): Wavelength of the X-ray source, in angstroms.

    Returns:
        numpy.ndarray: Array of two-theta angles, in degrees.
    """
    if q is not None:
        return 2 * np.arcsin(q * wavelength / (4 * np.pi))
    elif two_theta is not None:
        return (4 * np.pi / wavelength) * np.sin(np.deg2rad(two_theta) / 2)
    else:
        raise ValueError("Either q or two_theta must be provided.")


def estimate_kalpha_wavelengths(source_material):
    """
    Estimate the K-alpha1 and K-alpha2 wavelengths of an X-ray source given the material 
    of the source.

    Args:
        source_material (str): Material of the X-ray source, such as 'Cu', 'Fe', 'Mo',
        'Ag', 'In', 'Ga', etc.

    Returns:
        Tuple[float, float]: Estimated K-alpha1 and K-alpha2 wavelengths of the X-ray
        source, in angstroms.
    """
    # Dictionary of K-alpha1 and K-alpha2 wavelengths for various X-ray source materials,
    # in angstroms
    kalpha_wavelengths = {
        'Cr': (2.2910, 2.2936),
        'Fe': (1.9359, 1.9397),
        'Cu': (1.5406, 1.5444),
        'Mo': (0.7093, 0.7136),
        'Ag': (0.5594, 0.5638),
        'In': (0.6535, 0.6577),
        'Ga': (1.2378, 1.2443)
    }

    try:
        kalpha1_wavelength, kalpha2_wavelength = kalpha_wavelengths[source_material]
    except KeyError as exc:
        raise ValueError("Unknown X-ray source material.") from exc

    return kalpha1_wavelength, kalpha2_wavelength
