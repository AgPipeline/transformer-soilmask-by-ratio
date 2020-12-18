"""Contains transformer configuration information
"""
from agpypeline.configuration import Configuration


class ConfigurationSoilmaskRatio(Configuration):
    """Configuration information"""
    # pylint: disable=too-few-public-methods
    # The version number of the transformer
    transformer_version = '1.0'

    # The transformer description
    transformer_description = 'Soil masks images through green:red ratio comparison'

    # Short name of the transformer
    transformer_name = 'SoilmaskRatio'

    # The sensor associated with the transformer
    transformer_sensor = 'stereoTop'

    # The transformer type (eg: 'rgbmask', 'plotclipper')
    transformer_type = 'rgbmask'

    # The name of the author of the extractor
    author_name = 'Chris Schnaufer'

    # The email of the author of the extractor
    author_email = 'schnaufer@arizona.edu'

    # Contributors to this transformer
    contributors = ["Andrew  French"]

    # Repository URI of where the source code lives
    repository = 'https://github.com/AgPipeline/transformer-soilmask-by-ratio'

    # Hard-coded override of base docker image (used when Dockerfile is generated)
    # If a name is entered here it will be used to populate the "FROM" field of the Dockerfile
    base_docker_image_override_name = ''
