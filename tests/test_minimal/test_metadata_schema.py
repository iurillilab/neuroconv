import traceback
import unittest
from pathlib import Path

import jsonschema
import pytest

from neuroconv.utils import load_dict_from_file
from neuroconv.utils.json_schema import validate_metadata


def test_metadata_schema():
    metadata_schema = load_dict_from_file(
        Path(__file__).parent.parent.parent / "src" / "neuroconv" / "schemas" / "metadata_schema.json"
    )

    metadata = dict(
        NWBFile=dict(
            session_start_time="2020-01-01T00:00:00",
            session_description="Auto-generated by neuroconv",
            identifier="1234",
        ),
        Ophys=dict(
            Devices=[
                dict(
                    name="ImagingDevice",
                ),
            ],
            Fluorescence=dict(
                name="Fluorescence",
                PlaneSegmentationChan1Plane0=dict(
                    raw=dict(name="RoiResponseSeriesChan1Plane0", description="raw fluorescence signal"),
                    deconvolved=dict(name="DeconvolvedChan1Plane0", description="deconvolved fluorescence signal"),
                    neuropil=dict(name="NeuropilChan1Plane0", description="neuropil fluorescence signal"),
                ),
                PlaneSegmentationChan1Plane1=dict(
                    raw=dict(name="RoiResponseSeriesChan1Plane0", description="raw fluorescence signal"),
                    deconvolved=dict(name="DeconvolvedChan1Plane0", description="deconvolved fluorescence signal"),
                    neuropil=dict(name="NeuropilChan1Plane0", description="neuropil fluorescence signal"),
                ),
            ),
            DfOverF=dict(
                name="DfOverF",
                PlaneSegmentationChan1Plane0=dict(
                    dff=dict(name="RoiResponseSeriesChan1Plane0", description="Array of df/F traces."),
                ),
                PlaneSegmentationChan1Plane1=dict(
                    dff=dict(name="RoiResponseSeriesChan1Plane0", description="Array of df/F traces."),
                ),
            ),
            SegmentationImages=dict(
                name="SegmentationImages",
                PlaneSegmentationChan1Plane0=dict(
                    raw=dict(name="PlaneSegmentationChan1Plane0", description="raw segmentation image"),
                    neuropil=dict(name="PlaneSegmentationChan1Plane0", description="neuropil segmentation image"),
                ),
            ),
        ),
    )

    validate_metadata(metadata=metadata, schema=metadata_schema)

def test_invalid_ophys_metadata():
    metadata_schema = load_dict_from_file(
        Path(__file__).parent.parent.parent / "src" / "neuroconv" / "schemas" / "metadata_schema.json"
    )

    metadata = dict(
        NWBFile=dict(
            session_start_time="2020-01-01T00:00:00",
            session_description="Auto-generated by neuroconv",
            identifier="1234",
        ),
        Ophys=dict(
            Devices=[],
            Fluorescence={
                "name": "Fluorescence",
                "fluorescence_chan1_plane0": dict(),  # Value Unchecked
                "FluorescenceChan1Plane0": dict(),
                "FluorescenceChan1Plane1": dict(
                    raw=dict(),
                ),
            },
            DFOverF={
                "name": "DfOverF",
                "df_chan1_plane0": dict(),  # Value Unchecked
                "DFChan1Plane0": dict(),
                "DFChan1Plane1": dict(
                    raw=dict(),
                ),
            },
            SegmentationImages={
                "name": "SegmentationImages",
                "segmentation_chan1_plane0": dict(),  # Value Unchecked
                "SegmentationChan1Plane0": dict(),
                "SegmentationChan1Plane1": dict(
                    raw=dict(),
                ),
            },
        ),
    )

    expected_errors = [
        dict(
            message="'fluorescence_chan1_plane0' does not match any of the regexes: '^(?!name$)[a-zA-Z0-9]+$'",
            path="$.Ophys.Fluorescence",
        ),
        dict(
            message="'df_chan1_plane0' does not match any of the regexes: '^(?!name$)[a-zA-Z0-9]+$'",
            path="$.Ophys.DFOverF",
        ),
        dict(
            message="'segmentation_chan1_plane0' does not match any of the regexes: '^(?!(name|description)$)[a-zA-Z0-9]+$'",
            path="$.Ophys.SegmentationImages",
        ),
        dict(
            message="{} does not have enough properties",
            path="$.Ophys.Fluorescence.FluorescenceChan1Plane0",
        ),
        dict(
            message="{} does not have enough properties",
            path="$.Ophys.DFOverF.DFChan1Plane0",
        ),
        dict(
            message="{} does not have enough properties",
            path="$.Ophys.SegmentationImages.SegmentationChan1Plane0",
        ),
        dict(
            message="'name' is a required property",
            path="$.Ophys.Fluorescence.FluorescenceChan1Plane1.raw",
        ),
        dict(
            message="'name' is a required property",
            path=f"$.Ophys.DFOverF.DFChan1Plane1.raw",
        ),
        dict(
            message="'name' is a required property",
            path="$.Ophys.SegmentationImages.SegmentationChan1Plane1.raw",
        ),
        dict(
            message="'description' is a required property",
            path="$.Ophys.Fluorescence.FluorescenceChan1Plane1.raw",
        ),
        dict(
            message="'description' is a required property",
            path="$.Ophys.DFOverF.DFChan1Plane1.raw",
        ),
    ]


    validator = jsonschema.Draft7Validator(metadata_schema)

    errors = [{ "message": error.message, "path": error.json_path }  for error in validator.iter_errors(metadata)]

    def sorting_fn(o):
        return o["message"]

    errors.sort(key=sorting_fn)
    expected_errors.sort(key=sorting_fn)

    assert len(errors) == len(expected_errors)
    
    for error in errors:
        assert error in expected_errors

def test_invalid_ophys_plane_metadata():
    metadata_schema = load_dict_from_file(
        Path(__file__).parent.parent.parent / "src" / "neuroconv" / "schemas" / "metadata_schema.json"
    )

    expected_errors = [
        dict(
            message="{'name': 'Fluorescence'} does not have enough properties",
            path=f"$.Ophys.Fluorescence",
        ),
        dict(
            message="{'name': 'DfOverF'} does not have enough properties",
            path=f"$.Ophys.DFOverF",
        ),
        dict(
            message="{'name': 'SegmentationImages'} does not have enough properties",
            path=f"$.Ophys.SegmentationImages",
        ),
    ]


    # Just a name is not enough
    metadata = dict(
        NWBFile=dict(
            session_start_time="2020-01-01T00:00:00",
            session_description="Auto-generated by neuroconv",
            identifier="1234",
        ),
        Ophys=dict(
            Devices=[],
            Fluorescence={"name": "Fluorescence"},
            DFOverF={"name": "DfOverF"},
            SegmentationImages={"name": "SegmentationImages"},
        ),
    )

    validator = jsonschema.Draft7Validator(metadata_schema)
    errors = [{ "message": error.message, "path": error.json_path }  for error in validator.iter_errors(metadata)]

    def sorting_fn(o):
        return o["message"]

    errors.sort(key=sorting_fn)
    expected_errors.sort(key=sorting_fn)

    assert len(errors) == len(expected_errors)

    for error in errors:
        assert error in expected_errors
    
def test_ophys_plane_fix():
    metadata_schema = load_dict_from_file(
        Path(__file__).parent.parent.parent / "src" / "neuroconv" / "schemas" / "metadata_schema.json"
    )


    # Just a name is not enough
    metadata = dict(
        NWBFile=dict(
            session_start_time="2020-01-01T00:00:00",
            session_description="Auto-generated by neuroconv",
            identifier="1234",
        ),
        Ophys=dict(
             Devices=[],
            Fluorescence={
                "name": "Fluorescence",
                "FluorescenceChan1Plane1": dict(
                    raw=dict(name="FluorescenceChan1Plane0", description="basic description"),
                ),
            },
            DFOverF={
                "name": "DfOverF",
                "DFChan1Plane1": dict(
                    raw=dict(name="DFChan1Plane0", description="basic description"),
                ),
            },
            SegmentationImages={
                "name": "SegmentationImages",
                "SegmentationChan1Plane1": dict(
                    raw=dict(name="SegmentationChan1Plane0", description="basic description"),
                ),
            },
        ),
    )

    validator = jsonschema.Draft7Validator(metadata_schema)
    errors = [ error.message for error in validator.iter_errors(metadata) ]
    assert len(errors) == 0
