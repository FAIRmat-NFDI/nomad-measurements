# How to install this plugin

This plugin can be used in a NOMAD Oasis installation. Please visit the NOMAD documentation for details on [how to setup an NOMAD Oasis](https://nomad-lab.eu/prod/v1/staging/docs/howto/oasis/install.html).



## Add This Plugin to Your NOMAD Oasis installation

Read the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/plugins/plugins.html#add-a-plugin-to-your-nomad) for all details on how to deploy the plugin on your NOMAD instance.

We recommend writing your own NOMAD docker image which includes the NOMAD plugins you want to deploy. Please follow [part 4 of FAIRmat Tutorial 13]() to set up your own NOMAD image writing workflow.

You need to modify the `plugins.txt` file and add the following lines:

```
git+https://github.com/FAIRmat-NFDI/nomad-measurements.git
``` 

This will add the latest version of the NOMAD-Measurements Plugin to your NOMAD Oasis image. 
If you want to add a specific version of the plugin you will need to provide the commit sha, for example:

```
git+https://github.com/FAIRmat-NFDI/nomad-measurements.git@f19c0e3b175613ec026ef36c849af3474c42cf52
```

## Local installation of the plugin in your Python environment

`nomad-measurements` can be installed from PyPI using `pip`.
Currently we require features in `nomad-lab` which are not published to PyPI.
In order to install these a `--index-url` needs to be provided:
```sh
pip install nomad-measurements --index-url https://gitlab.mpcdf.mpg.de/api/v4/projects/2187/packages/pypi/simple
```


