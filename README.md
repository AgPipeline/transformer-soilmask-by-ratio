# Transformer Soil Mask by Ratio

Converts an RGB image into a soil mask in which the soil is represented as black.

This implementation uses a comparison of the ratio between green and red to determine if a pixel represents a plant.

## Algorithm Description

For each pixel, the green to red ratio is calculated.
If the ratio is equal to or above the threshold, it is considered to represent a part of a plant.

Steps:

1. Split image data into R,G,B channel, and make a tmp image.
2. For each pixel, if the G to  R ratio is equal to or greater than the threshold ratio, make this pixel as foreground, and set the tmp pixel value to 255, so all tmp pixels are either 0 or 255.
3. Output ratio = foreground pixel count / total pixel count
4. The masked image is then written to disk where a mask value of 0 represents soil. A mask value of 255 results in the original pixel being retained.

### Parameters

* G to R ratio is set to 1.0 for normal situation. This can be overridden via a command line parameter 

## Use 

### Sample Docker Command line

First build the Docker image, using the Dockerfile, and tag it agdrone/transformer-soilmask:2.1. 
Read about the [docker build](https://docs.docker.com/engine/reference/commandline/build/) command if needed.

```bash
docker build -t agdrone/transformer-soilmask-by-ratio:1.0 ./
```

There is one file needed for running the Docker image.
The `orthomosiac.tif` file is an Orthomosaic image that is to have the soil removed.
This file can be retrieved using the following commands (more files than needed are extracted):
```bash
mkdir test_data
curl -X GET https://de.cyverse.org/dl/d/3C8A23C0-F77A-4598-ADC4-874EB265F9B0/scif_test_data.tar.gz -o test_data/scif_test_data.tar.gz
tar -xzvf test_data/scif_test_data.tar.gz -C test_data/
```

Below is a sample command line that shows how the soil mask Docker image could be run.
An explanation of the command line options used follows.
Be sure to read up on the [docker run](https://docs.docker.com/engine/reference/run/) command line for more information.

```bash
docker run --rm --mount "src=${PWD}/test_data,target=/mnt,type=bind" agdrone/transformer-soilmask-by-ratio:1.0 --ratio 1.25 --working_space "/mnt" "/mnt/orthomosaic.tif"
```

This example command line assumes the source files are located in the `test_data` folder off the current folder.
The name of the image to run is `agdrone/transformer-soilmask-by-ratio:1.0`.

We are using the same folder for the source files and the output files.
By using multiple `--mount` options, the source and output files can be separated.

**Docker commands** \
Everything between 'docker' and the name of the image are docker commands.

- `run` indicates we want to run an image
- `--rm` automatically delete the image instance after it's run
- `--mount "src=${PWD}/test_data,target=/mnt,type=bind"` mounts the `${PWD}/test_data` folder to the `/mnt` folder of the running image

We mount the `${PWD}/test_data` folder to the running image to make files available to the software in the image.

**Image's commands** \
The command line parameters after the image name are passed to the software inside the image.
Note that the paths provided are relative to the running image (see the --mount option specified above).

- `--ratio 1.25` specifies that the the threshold ratio of green to red per-pixel is 1.25:1 (per-pixel ratios below this are masked out)
- `--working_space "/mnt"` specifies the folder to use as a workspace
- `"/mnt/orthomosaic.tif"` is the name of the image to mask

## Acceptance Testing

There are automated test suites that are run via [GitHub Actions](https://docs.github.com/en/actions).
In this section we provide details on these tests so that they can be run locally as well.

These tests are run when a [Pull Request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests) or [push](https://docs.github.com/en/github/using-git/pushing-commits-to-a-remote-repository) occurs on the `develop` or `master` branches.
There may be other instances when these tests are automatically run, but these are considered the mandatory events and branches.

### PyLint and PyTest

These tests are run against any Python scripts that are in the repository.

[PyLint](https://www.pylint.org/) is used to both check that Python code conforms to the recommended coding style, and checks for syntax errors.
The default behavior of PyLint is modified by the `pylint.rc` file in the [Organization-info](https://github.com/AgPipeline/Organization-info) repository.
Please also refer to our [Coding Standards](https://github.com/AgPipeline/Organization-info#python) for information on how we use [pylint](https://www.pylint.org/).

The following command can be used to fetch the `pylint.rc` file:
```bash
wget https://raw.githubusercontent.com/AgPipeline/Organization-info/master/pylint.rc
```

Assuming the `pylint.rc` file is in the current folder, the following command can be used against the `soilmask.py` file:
```bash
# Assumes Python3.7+ is default Python version
python -m pylint --rcfile ./pylint.rc soilmask.py
``` 

In the `tests` folder there are testing scripts; their supporting files are in the `test_data` folder.
The tests are designed to be run with [Pytest](https://docs.pytest.org/en/stable/).
When running the tests, the root of the repository is expected to be the starting directory.

These tests use some of the files downloaded from [CyVerse](https://de.cyverse.org/dl/d/3C8A23C0-F77A-4598-ADC4-874EB265F9B0/scif_test_data.tar.gz).
The following commands download and extracts the files in this archive:
```bash
curl -X GET https://de.cyverse.org/dl/d/3C8A23C0-F77A-4598-ADC4-874EB265F9B0/scif_test_data.tar.gz -o test_data/scif_test_data.tar.gz
tar -xzvf test_data/scif_test_data.tar.gz -C test_data/
```

The command line for running the tests is as follows:
```bash
# Assumes Python3.7+ is default Python version
python -m pytest -rpP
```

If [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/) is installed, it can be used to generate a code coverage report as part of running PyTest.
The code coverage report shows how much of the code has been tested; it doesn't indicate **how well** that code has been tested.
The modified PyTest command line including coverage is:
```bash
# Assumes Python3.7+ is default Python version
python -m pytest --cov=. -rpP 
```

### Docker Testing

The Docker testing Workflow replicate the examples in this document to ensure they continue to work.
