#!/usr/bin/env python3
"""My nifty transformer
"""

import argparse
import logging
import os
import numpy as np
from osgeo import gdal
import cv2

from agpypeline import algorithm, entrypoint, geoimage
from agpypeline.environment import Environment
from agpypeline.checkmd import CheckMD

from configuration import ConfigurationSoilmaskRatio


# Define the default green-red ratio value
GREEN_RED_RATIO = 1.0

# Maximum value a pixel can be
MAX_PIXEL_VAL = 255

class __internal__:
    """Class for functions intended for internal use only for this file
    """
    def __init__(self):
        """Performs initialization of class instance
        """

    @staticmethod
    def get_maskfilename(filename: str) -> str:
        """Returns the name of the file to use as a mask. Any path information
           in the filename parameter is not returned.
        Arguments:
            filename: the name of the file to convert to a mask name
        Return:
            The name of the mask file
        """
        base, ext = os.path.splitext(os.path.basename(filename))

        return base + "_mask" + ext

    @staticmethod
    def prepare_metadata_for_geotiff(transformer_info: dict = None) -> dict:
        """Create geotiff-embeddable metadata from extractor_info and other metadata pieces.
        Arguments:
            transformer_info: details about the transformer
        Return:
            A dict containing information to save with an image
        """
        extra_metadata = {}

        if transformer_info:
            extra_metadata["transformer_name"] = str(transformer_info.get("name", ""))
            extra_metadata["transformer_version"] = str(transformer_info.get("version", ""))
            extra_metadata["transformer_author"] = str(transformer_info.get("author", ""))
            extra_metadata["transformer_description"] = str(transformer_info.get("description", ""))
            if "repository" in transformer_info and transformer_info["repository"] and \
                    "repUrl" in transformer_info["repository"]:
                extra_metadata["transformer_repo"] = str(transformer_info["repository"]["repUrl"])
            else:
                extra_metadata["transformer_repo"] = ""

        return extra_metadata

    @staticmethod
    def gen_plant_mask(color_img: np.ndarray, ratio: float) -> np.ndarray:
        """Generates an image with plants masked in.
        Arguments:
            color_img: RGB image to mask
            ratio: the red to green ratio
        Return:
            An RGB image with plants masked in
        """
        # Generate the green to red ratio comparison value to make it easy to filter
        # For a given value of green, red can't be larger than this value else the ratio is exceeded (too much red)
        max_red_vals = []
        for idx in range(0, MAX_PIXEL_VAL + 1):
            max_red_vals.append(min(idx / ratio, MAX_PIXEL_VAL))
        red_limit = np.array(max_red_vals)

        # Isolate each channel
        r_channel = color_img[:, :, 2]
        g_channel = color_img[:, :, 1]
        b_channel = color_img[:, :, 0]

        # Calculate what meets the ratio
        sub_img = red_limit[g_channel.astype('int')] >= r_channel

        mask = np.zeros_like(b_channel)
        mask[sub_img] = MAX_PIXEL_VAL

        return mask

    @staticmethod
    def gen_rgb_mask(img: np.ndarray, bin_mask: np.ndarray) -> np.ndarray:
        """Applies the mask to the image
        Arguments:
            img: the source image to mask
            bin_mask: the mask to apply to the image
        Return:
            A new image that had the mask applied
        """
        rgb_mask = cv2.bitwise_and(img[:, :, 0:3], img[:, :, 0:3], mask=bin_mask)

        if img.shape[2] > 3:
            rgb_mask = np.concatenate((rgb_mask, img[:, :, 3:]), axis=2)

        return rgb_mask


def soilmask_by_ratio(filename: str, ratio: float = GREEN_RED_RATIO) -> tuple:
    """Applies a soil mask to the file by applying a green-to-red ratio
    Arguments:
        filename: the file to mask (not modified)
        ratio: the ratio (as a fraction) serving as the lower bound for determining plant vs. soil
    Return:
         A tuple containing the ratio of plant-to-total pixels, and the mask as an numpy array
    Notes:
        Any ratio that equals or exceeds the passed in value is considered a plant pixel and is not masked
        No checks are made to the image for saturation or under exposure
    """
    # Check the ratio value for sanity
    if ratio <= 0:
        raise RuntimeError("Ratio value for soil masking is zero or a negative number: %s" % str(ratio))

    # Load the image
    img = np.rollaxis(gdal.Open(filename).ReadAsArray().astype(np.uint8), 0, 3)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB if img.shape[2] < 4 else cv2.COLOR_BGRA2RGBA)

    # Generate mask
    bin_mask = __internal__.gen_plant_mask(img, ratio)

    count = np.count_nonzero(bin_mask)
    ratio = count / float(bin_mask.size)

    rgb_mask = __internal__.gen_rgb_mask(img, bin_mask)

    return ratio, rgb_mask


class SoilmaskByRatio(algorithm.Algorithm):
    """Used  as base for simplified RGB transformers"""

    @property
    def supported_file_ext(self) -> tuple:
        """Returns a tuple of supported file extensions in lowercase (with the preceding dot: eg '.tif')"""
        return '.tiff', '.tif'

    def add_parameters(self, parser: argparse.ArgumentParser) -> None:
        """Adds parameters
        Arguments:
            parser: instance of argparse
        """
        parser.add_argument('--out_file', type=str, help='the path to save the masked file to')
        parser.add_argument('--ratio', type=float, default=GREEN_RED_RATIO,
                            help='the lower bound decimal value of green-to-red ratio to be considered plant (eg: 0.75 or 1.2)' \
                                 ' default %s' % str(GREEN_RED_RATIO))

    def check_continue(self, environment: Environment, check_md: CheckMD, transformer_md: dict, full_md: list) -> tuple:
        """Checks if conditions are right for continuing processing
        Arguments:
            environment: instance of environment class
            check_md: request specific metadata
            transformer_md: metadata associated with previous runs of the transformer
            full_md: the full set of metadata available to the transformer
        Return:
            Returns a tuple containing the return code for continuing or not, and
            an error message if there's an error
        """
        # pylint: disable=unused-argument
        result = {'code': -1002, 'message': "No TIFF files were specified for processing"}

        # Ensure we have a TIFF file
        if check_md:
            files = check_md.get_list_files()
            try:
                for one_file in files:
                    ext = os.path.splitext(one_file)[1].lower()
                    if ext in self.supported_file_ext:
                        result['code'] = 0
                        break
            except Exception as ex:
                if logging.getLogger().level == logging.DEBUG:
                    logging.exception("Exception caught in check_continue")
                result['code'] = -1
                result['error'] = "Exception caught processing file list: %s" % str(ex)
        else:
            result['code'] = -1
            result['error'] = "Check metadata parameter is not configured to provide a list of files"

        return (result['code'], result['error']) if 'error' in result else (result['code'])

    def perform_process(self, environment: Environment, check_md: CheckMD, transformer_md: dict, full_md: list) -> dict:
        """Performs the processing of the data
        Arguments:
            environment: instance of environment class
            check_md: request specific metadata
            transformer_md: metadata associated with previous runs of the transformer
            full_md: the full set of metadata available to the transformer
        Return:
            Returns a dictionary with the results of processing
        """
        # Disable pylint warnings that reduce readability
        # pylint: disable=unused-argument, too-many-branches
        result = {}
        file_md = []

        # Loop through the files
        try:
            for one_file in check_md.get_list_files():
                # Check file by type
                ext = os.path.splitext(one_file)[1].lower()
                if ext not in self.supported_file_ext:
                    continue
                if not os.path.exists(one_file):
                    logging.warning("Unable to access file '%s'", one_file)
                    continue

                # Get the image's EPSG code
                epsg = geoimage.get_epsg(one_file)
                if epsg is not None:
                    # Get the bounds of the image to see if we can process it.
                    bounds = geoimage.image_get_geobounds(one_file)

                    if bounds is None:
                        logging.warning("Unable to get bounds of georeferenced image: '%s'",
                                        os.path.basename(one_file))
                        continue

                # Get the mask name
                if environment.args.out_file:
                    rgb_mask_tif = environment.args.out_file
                    if not os.path.dirname(rgb_mask_tif):
                        rgb_mask_tif = os.path.join(check_md.working_folder, rgb_mask_tif)
                else:
                    # Use the original name
                    rgb_mask_tif = os.path.join(check_md.working_folder, __internal__.get_maskfilename(one_file))

                # Create the mask file
                logging.debug("Creating mask file '%s'", rgb_mask_tif)
                mask_ratio, mask_rgb = soilmask_by_ratio(one_file, environment.args.ratio)
                if mask_rgb is None:
                    logging.warning("Skipping over image that failed quality check: %s", one_file)
                    continue

                # Bands must be reordered to avoid swapping R and B
                mask_rgb = cv2.cvtColor(mask_rgb, cv2.COLOR_BGR2RGB if mask_rgb.shape[2] < 4 else cv2.COLOR_BGRA2RGBA)

                transformer_info = environment.generate_transformer_md()

                image_md = __internal__.prepare_metadata_for_geotiff(transformer_info)
                if epsg:
                    geoimage.create_geotiff(mask_rgb, bounds, rgb_mask_tif, epsg, None, False, image_md, compress=True)
                else:
                    geoimage.create_tiff(mask_rgb, rgb_mask_tif, None, False, image_md, compress=True)

                transformer_md = {
                    'name': transformer_info['name'],
                    'version': transformer_info['version'],
                    'ratio': mask_ratio
                }

                new_file_md = {'path': rgb_mask_tif,
                               'key': ConfigurationSoilmaskRatio.transformer_sensor,
                               'metadata': {
                                   'data': transformer_md
                               }
                              }
                file_md.append(new_file_md)

            result['code'] = 0
            result['file'] = file_md

        except Exception as ex:
            if logging.getLogger().level == logging.DEBUG:
                logging.exception("Exception caught in perform_process")
            result['code'] = -1001
            result['error'] = "Exception caught masking files: %s" % str(ex)

        return result


if __name__ == "__main__":
    CONFIGURATION = ConfigurationSoilmaskRatio()
    entrypoint.entrypoint(CONFIGURATION, SoilmaskByRatio())
