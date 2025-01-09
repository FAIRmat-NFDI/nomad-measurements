# Welcome to the NOMAD-measurements Plugin Documentation

Welcome to the official documentation for the **NOMAD-measurements Plugin**! This plugin is designed to provide structured data schemas for storing experimental measurement data in alignment with the FAIR (Findable, Accessible, Interoperable, and Reusable) principles. It serves as a community or standard plugin, offering commonly used schemas and classes/sections for measurement data that can be shared across a community.

## Supported Measurement Techniques

Currently, this plugin supports the following measurement techniques:

- **X-ray Diffraction (XRD)**: Supports 1D line scans and 2D Reciprocal Space 
Mapping (RSM) scans. Supports automatic parsing of data for the following file formats
(read more [here](explanation/schemas.md#x-ray-diffraction)):
  - Panalytical: `*.xrdml`
  - Bruker: `*.brml`
  - Rigaku: `*.rasx`

- **UV-Vis-NIR Transmission**: Supports automatic parsing of data for the following 
file formats (read more [here](explanation/schemas.md#transmission-spectrophotometry)):
  - Perkin Elmers: `*.asc`
 
- **Physical Properies Measurement System (PPMS)**: Supports automatic parsing of
measurement files and sequence files from the Quantum Design PPMS. For now, ETO and 
ACT modes are supported. Supported file formats:
  - QuantumDesign PPMS: `*.dat ` and `*.seq`

Additional measurement techniques are actively being developed and will be included soon, including:

- Raman Spectroscopy
- X-ray Fluorescence (XRF)

Stay tuned for updates as more methods become available!

## What You Will Find in This Documentation

This documentation builds upon the general [NOMAD documentation](https://nomad-lab.eu/prod/v1/staging/docs/explanation/data.html). Here, you will find comprehensive guides on:

- **Using the Plugin**: Step-by-step instructions on how to integrate and use the NOMAD Measurements Plugin in your NOMAD Oasis.
- **Data Structures and Supported Methods**: Detailed descriptions of the available schemas, sections, and supported measurement techniques.
- **Contributing**: Learn how you can contribute to the ongoing development of this plugin.

## About NOMAD

NOMAD is an open-source data management platform tailored for materials science, designed to follow the FAIR principles. It offers a robust framework for managing and sharing materials data in a standardized and interoperable manner. To learn more about NOMAD, visit the [official homepage](https://nomad-lab.eu).


We hope this documentation provides all the information you need to make the most of the NOMAD Measurements Plugin. Feel free to [contact](contact.md) us for further questions.

