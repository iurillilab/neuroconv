"""Authors: Cody Baker and Ben Dichter."""
from typing import Optional

import numpy as np
from pynwb import NWBFile
from pynwb.device import Device
from pynwb.ecephys import ElectrodeGroup, ElectricalSeries

from ...baseextractorinterface import BaseExtractorInterface
from ...utils import get_schema_from_hdmf_class, get_base_schema, FilePathType


class BaseRecordingExtractorInterface(BaseExtractorInterface):
    """Parent class for all RecordingExtractorInterfaces."""

    ExtractorModuleName: Optional[str] = "spikeinterface.extractors"

    def __init__(self, verbose: bool = True, es_key: str = "ElectricalSeries", **source_data):
        """
        Parameters
        ----------
        verbose : bool, default True
            If True, will print out additional information.
        source_data : dict
            key-value pairs of extractor-specific arguments.
        es_key : str, default: "ElectricalSeries"
            Key of this ElectricalSeries in the metadata dictionary

        """
        super().__init__(**source_data)
        self.recording_extractor = self.get_extractor()(**source_data)
        self.subset_channels = None
        self.verbose = verbose
        self.es_key = es_key  # For automatic metadata extraction

    def get_metadata_schema(self) -> dict:
        """Compile metadata schema for the RecordingExtractor."""
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"] = get_base_schema(tag="Ecephys")
        metadata_schema["properties"]["Ecephys"]["required"] = ["Device", "ElectrodeGroup"]
        metadata_schema["properties"]["Ecephys"]["properties"] = dict(
            Device=dict(type="array", minItems=1, items={"$ref": "#/properties/Ecephys/properties/definitions/Device"}),
            ElectrodeGroup=dict(
                type="array", minItems=1, items={"$ref": "#/properties/Ecephys/properties/definitions/ElectrodeGroup"}
            ),
            Electrodes=dict(
                type="array",
                minItems=0,
                renderForm=False,
                items={"$ref": "#/properties/Ecephys/properties/definitions/Electrodes"},
            ),
        )
        # Schema definition for arrays
        metadata_schema["properties"]["Ecephys"]["properties"]["definitions"] = dict(
            Device=get_schema_from_hdmf_class(Device),
            ElectrodeGroup=get_schema_from_hdmf_class(ElectrodeGroup),
            Electrodes=dict(
                type="object",
                additionalProperties=False,
                required=["name"],
                properties=dict(
                    name=dict(type="string", description="name of this electrodes column"),
                    description=dict(type="string", description="description of this electrodes column"),
                ),
            ),
        )

        if self.es_key is not None:
            metadata_schema["properties"]["Ecephys"]["properties"].update(
                {self.es_key: get_schema_from_hdmf_class(ElectricalSeries)}
            )

        return metadata_schema

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        channel_groups_array = self.recording_extractor.get_channel_groups()
        unique_channel_groups = set(channel_groups_array) if channel_groups_array is not None else ["ElectrodeGroup"]
        electrode_metadata = [
            dict(name=str(group_id), description="no description", location="unknown", device="DeviceEcephys")
            for group_id in unique_channel_groups
        ]

        metadata["Ecephys"] = dict(
            Device=[dict(name="DeviceEcephys", description="no description")],
            ElectrodeGroup=electrode_metadata,
        )

        if self.es_key is not None:
            metadata["Ecephys"][self.es_key] = dict(
                name=self.es_key, description=f"Acquisition traces for the {self.es_key}."
            )

        return metadata

    def get_original_timestamps(self) -> np.ndarray:
        return self.get_extractor()(**self.source_data).get_times()

    def get_timestamps(self) -> np.ndarray:
        return self.recording_extractor.get_times()

    def align_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self.recording_extractor.set_times(times=aligned_timestamps)

    def subset_recording(self, stub_test: bool = False):
        """
        Subset a recording extractor according to stub and channel subset options.

        Parameters
        ----------
        stub_test : bool, default: False
        """
        kwargs = dict()
        if stub_test:
            num_frames = 100
            end_frame = min([num_frames, self.recording_extractor.get_num_frames()])
            kwargs.update(end_frame=end_frame)
        if self.subset_channels is not None:
            kwargs.update(channel_ids=self.subset_channels)
        recording_extractor = self.recording_extractor.frame_slice(start_frame=0, end_frame=end_frame)
        return recording_extractor

    def run_conversion(
        self,
        nwbfile_path: Optional[FilePathType] = None,
        nwbfile: Optional[NWBFile] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = False,
        stub_test: bool = False,
        starting_time: Optional[float] = None,
        write_as: str = "raw",  # Literal["raw", "processed"]
        write_electrical_series: bool = True,
        compression: Optional[str] = None,
        compression_opts: Optional[int] = None,
        iterator_type: str = "v2",
        iterator_opts: Optional[dict] = None,
    ):
        """
        Primary function for converting raw (unprocessed) RecordingExtractor data to the NWB standard.

        Parameters
        ----------
        nwbfile_path : FilePathType
            Path for where to write or load (if overwrite=False) the NWBFile.
            If specified, this context will always write to this location.
        nwbfile : NWBFile, optional
            NWBFile to which the recording information is to be added
        metadata : dict, optional
            metadata info for constructing the NWB file.
            Should be of the format::

                metadata['Ecephys']['ElectricalSeries'] = dict(name=my_name, description=my_description)
        overwrite: bool, default: False
            Whether to overwrite the NWB file if one exists at the nwbfile_path.
        The default is False (append mode).
        starting_time : float, optional
            Sets the starting time of the ElectricalSeries to a manually set value.
        stub_test : bool, default: False
            If True, will truncate the data to run the conversion faster and take up less memory.
        write_as : {'raw', 'lfp', 'processed'}
        write_electrical_series : bool, default: True
            Electrical series are written in acquisition. If False, only device, electrode_groups,
            and electrodes are written to NWB.
        compression : {'gzip', 'lzf', None}
            Type of compression to use.
            Set to None to disable all compression.
        compression_opts : int, default: 4
            Only applies to compression="gzip". Controls the level of the GZIP.
        iterator_type : {'v2', 'v1'}
            The type of DataChunkIterator to use.
            'v1' is the original DataChunkIterator of the hdmf data_utils.
            'v2' is the locally developed RecordingExtractorDataChunkIterator, which offers full control over chunking.
        iterator_opts : dict, optional
            Dictionary of options for the RecordingExtractorDataChunkIterator (iterator_type='v2').
            Valid options are
                buffer_gb : float, default: 1.0
                    In units of GB. Recommended to be as much free RAM as available. Automatically calculates suitable
                    buffer shape.
                chunk_mb : float. default: 1.0
                    Should be below 1 MB. Automatically calculates suitable chunk shape.
            If manual specification of buffer_shape and chunk_shape are desired, these may be specified as well.
        """
        from ...tools.spikeinterface import write_recording

        if stub_test or self.subset_channels is not None:
            recording = self.subset_recording(stub_test=stub_test)
        else:
            recording = self.recording_extractor

        write_recording(
            recording=recording,
            nwbfile_path=nwbfile_path,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=overwrite,
            verbose=self.verbose,
            starting_time=starting_time,
            write_as=write_as,
            write_electrical_series=write_electrical_series,
            es_key=self.es_key,
            compression=compression,
            compression_opts=compression_opts,
            iterator_type=iterator_type,
            iterator_opts=iterator_opts,
        )
