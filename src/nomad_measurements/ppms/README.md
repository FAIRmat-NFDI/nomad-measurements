# The PPMSMeasurement plugin

This README describes the PPMSMeasurement plugin for NOMAD. This plugin can read in a measurement file from a QuantumDesign Physical Properties Measurement System (PPMS) and separates the different measurements from the file. To support this process, the respective sequence file can be provided.

**Important note:** For now, only ETO and ACT measurement modes are supported.

## Installation

To use the PPMSMeasurement plugin, install it according to [this](https://nomad-lab.eu/prod/v1/docs/howto/oasis/plugins_install.html) guide.

## Prerequisites

To use the PPMSMeasurement plugin, the following points have to be met:

- NOMAD with the PPMSMeasurement plugin and parser
- PPMS data file
- optionally PPMS sequence file

## Using the PPMSMeasurement plugin

To use the plugin, create a new upload in NOMAD and just upload the PPMS data file and optionally the sequence file. The parser will recognize them and creates an archive for PPMSMeasurement.

In this archive, the data file is split into separate measurements (field or temperature sweeps) and each of the is plotted versus the magnetic field.