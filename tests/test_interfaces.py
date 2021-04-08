from jsonschema import Draft7Validator
import numpy as np
from tempfile import mkdtemp
from shutil import rmtree
from pathlib import Path
from itertools import product

import cv2

from nwb_conversion_tools import interface_list
from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.datainterfaces.moviedatainterface import MovieInterface


def test_interface_schemas():
    for data_interface in interface_list:
        # check validity of source schema
        schema = data_interface.get_source_schema()
        Draft7Validator.check_schema(schema)

        # check validity of conversion options schema
        schema = data_interface.get_conversion_options_schema()
        Draft7Validator.check_schema(schema)


def test_movie_interface():
    test_dir = Path(mkdtemp())
    movie_file = test_dir / "test1.avi"
    nwbfile_path = str(test_dir / "test1.nwb")
    (nf, nx, ny) = (50, 640, 480)
    writer = cv2.VideoWriter(
        filename=str(movie_file),
        apiPreference=None,
        fourcc=cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
        fps=25,
        frameSize=(ny, nx),
        params=None
    )
    for k in range(nf):
        writer.write(np.random.randint(0, 255, (nx, ny, 3)).astype('uint8'))
    writer.release()

    class MovieTestNWBConverter(NWBConverter):
        data_interface_classes = dict(Movie=MovieInterface)
    source_data = dict(Movie=dict(file_paths=[movie_file]))
    converter = MovieTestNWBConverter(source_data)
    metadata = converter.get_metadata()

    # Default usage
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, overwrite=True)

    # This conversion option operates independently of all others
    converter.run_conversion(
        metadata=metadata,
        nwbfile_path=nwbfile_path,
        overwrite=True,
        conversion_options=dict(Movie=dict(starting_times=[123.]))
    )

    # These conversion options do not operate independently, so test them jointly
    conversion_options_testing_matrix = [
        dict(Movie=dict(external_mode=False, stub_test=x, chunk_data=y)) for x, y in product([True, False], repeat=2)
    ]
    for conversion_options in conversion_options_testing_matrix:
        converter.run_conversion(
            metadata=metadata,
            nwbfile_path=nwbfile_path,
            overwrite=True,
            conversion_options=conversion_options
        )
    rmtree(test_dir)