"""Unit tests for `get_default_dataset_configurations`."""
from pathlib import Path
from typing import Literal

import numcodecs
import numpy as np
import pytest
from hdmf.data_utils import DataChunkIterator
from hdmf_zarr import NWBZarrIO
from pynwb import NWBHDF5IO
from pynwb.testing.mock.base import mock_TimeSeries
from pynwb.testing.mock.file import mock_NWBFile

from neuroconv.tools.hdmf import SliceableDataChunkIterator
from neuroconv.tools.nwb_helpers import (
    configure_backend,
    get_default_backend_configuration,
)


@pytest.mark.parametrize(
    "case_name,iterator,iterator_options",
    [
        ("unwrapped", lambda x: x, dict()),
        ("generic", SliceableDataChunkIterator, dict()),
        ("classic", DataChunkIterator, dict(iter_axis=1, buffer_size=30_000 * 5)),
        # Need to hardcode buffer size in classic case or else it takes forever...
    ],
)
@pytest.mark.parametrize("backend", ["hdf5", "zarr"])
def test_simple_time_series_override(
    tmpdir: Path, case_name: str, iterator: callable, iterator_options: dict, backend: Literal["hdf5", "zarr"]
):
    BACKEND_NWB_IO = dict(hdf5=NWBHDF5IO, zarr=NWBZarrIO)

    array = np.zeros(shape=(30_000 * 5, 384), dtype="int16")
    data = iterator(array, **iterator_options)

    nwbfile = mock_NWBFile()
    time_series = mock_TimeSeries(name="TestTimeSeries", data=data)
    nwbfile.add_acquisition(time_series)

    backend_configuration = get_default_backend_configuration(nwbfile=nwbfile, backend=backend)
    dataset_configuration = backend_configuration.dataset_configurations["acquisition/TestTimeSeries/data"]

    smaller_chunk_shape = (30_000, 64)
    smaller_buffer_shape = (60_000, 192)
    higher_gzip_level = 5
    dataset_configuration.chunk_shape = smaller_chunk_shape
    dataset_configuration.buffer_shape = smaller_buffer_shape

    higher_gzip_level = 5
    if backend == "hdf5":
        dataset_configuration.compression_options = dict(level=higher_gzip_level)  # higher_gzip_level
    elif backend == "zarr":
        dataset_configuration.compression_options = dict(level=higher_gzip_level)

    configure_backend(nwbfile=nwbfile, backend_configuration=backend_configuration)

    if case_name != "unwrapped":  # TODO: eventually, even this case will be buffered automatically
        assert nwbfile.acquisition["TestTimeSeries"].data

    nwbfile_path = str(tmpdir / f"test_configure_{backend}_defaults_{case_name}_data.nwb.h5")
    with BACKEND_NWB_IO[backend](path=nwbfile_path, mode="w") as io:
        io.write(nwbfile)

    with BACKEND_NWB_IO[backend](path=nwbfile_path, mode="r") as io:
        written_nwbfile = io.read()
        written_data = written_nwbfile.acquisition["TestTimeSeries"].data

        assert written_data.chunks == smaller_chunk_shape

        if backend == "hdf5":
            assert written_data.compression == "gzip"
            assert print(written_data) is None
        elif backend == "zarr":
            assert written_data.compressor == numcodecs.GZip(level=5)
