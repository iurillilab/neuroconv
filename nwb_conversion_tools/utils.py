"""Authors: Cody Baker, Ben Dichter and Luiz Tauffer."""
import pynwb
import inspect
from datetime import datetime
import numpy as np


def get_base_schema(tag=None):
    base_schema = dict(
        required=[],
        properties={},
        type='object',
        tag=['' if tag is None else tag][0],
        additionalProperties=False
    )
    return base_schema


def get_root_schema():
    root_schema = get_base_schema()
    root_schema.update({
        "$schema": "http://json-schema.org/draft-07/schema#",
    })
    return root_schema


def get_input_schema():
    input_schema = get_root_schema()
    input_schema.update({
        "title": "Source data and conversion options",
        "description": "Schema for the source data and conversion options",
        "version": "0.1.0",
        "type": "object",
    })
    return input_schema


def get_schema_from_method_signature(class_method):
    input_schema = get_base_schema()
    for param in inspect.signature(class_method.__init__).parameters.values():
        if param.name != 'self':
            arg_spec = dict(name=param.name, type='string')
            if param.default is param.empty:
                input_schema['required'].append(param.name)
            elif param.default is not None:
                arg_spec.update(default=param.default)
            input_schema['properties'].update(arg_spec)
        input_schema['additionalProperties'] = param.kind == inspect.Parameter.VAR_KEYWORD

    return input_schema


def get_schema_from_hdmf_class(hdmf_class):
    schema = get_schema_from_docval(hdmf_class.__init__.__docval__)
    schema['tag'] = hdmf_class.__module__ + '.' + hdmf_class.__name__
    return schema


def get_schema_from_docval(docval):
    pynwb_link_types = [pynwb.device.Device, pynwb.ophys.ImagingPlane, pynwb.image.ImageSeries]
    schema = get_base_schema()
    for docval_arg in docval['args']:
        schema_arg = dict()

        # type float
        if docval_arg['type'] == 'float' or (isinstance(docval_arg['type'], tuple) and 'float' in docval_arg['type']):
            schema_arg[docval_arg['name']] = dict(type='number', description=docval_arg['doc'])

        # type string
        elif docval_arg['type'] is str or (isinstance(docval_arg['type'], tuple) and str in docval_arg['type']):
            schema_arg[docval_arg['name']] = dict(type='string', description=docval_arg['doc'])

        # type datetime
        elif docval_arg['type'] is datetime or (isinstance(docval_arg['type'], tuple) and datetime in docval_arg['type']):
            schema_arg[docval_arg['name']] = dict(type='string', description=docval_arg['doc'], format='date-time')

        # if link to another nwb object
        elif docval_arg['type'] in pynwb_link_types:
            target = docval_arg['type'].__module__ + '.' + docval_arg['type'].__name__
            schema_arg[docval_arg['name']] = dict(type='string', description=docval_arg['doc'], target=target)
        elif isinstance(docval_arg['type'], tuple) and any([t in pynwb_link_types for t in docval_arg['type']]):
            ind = np.where([t in pynwb_link_types for t in docval_arg['type']])[0][0]
            target = docval_arg['type'][ind].__module__ + '.' + docval_arg['type'][ind].__name__
            schema_arg[docval_arg['name']] = dict(type='string', description=docval_arg['doc'], target=target)

        # if TimeSeries, skip it
        elif docval_arg['type'] is pynwb.base.TimeSeries or (isinstance(docval_arg['type'], tuple) and pynwb.base.TimeSeries in docval_arg['type']):
            continue

        else:
            if not isinstance(docval_arg['type'], tuple):
                docval_arg_type = [docval_arg['type']]
            else:
                docval_arg_type = docval_arg['type']

            # if another nwb object (or list of nwb objects)
            if any([t.__module__.split('.')[0] == 'pynwb' for t in docval_arg_type if hasattr(t, '__module__')]):
                is_nwb = [t.__module__.split('.')[0] == 'pynwb' for t in list(docval_arg_type) if hasattr(t, '__module__')]
                items = [get_schema_from_hdmf_class(docval_arg_type[np.where(is_nwb)[0][0]])]
                schema_arg[docval_arg['name']] = dict(type='array', description=docval_arg['doc'], items=items, minItems=1, maxItems=1)
            else:
                continue

        # Check for default arguments
        if 'default' in docval_arg:
            if docval_arg['default'] is not None:
                schema_arg[docval_arg['name']].update(default=docval_arg['default'])
        else:
            schema['required'].append(docval_arg['name'])

        schema['properties'].update(schema_arg)

    if 'allow_extra' in docval:
        schema['additionalProperties'] = docval['allow_extra']

    return schema


def get_schema_for_NWBFile():
    schema = get_base_schema()
    schema['tag'] = 'pynwb.file.NWBFile'
    schema['required'] = ["session_description", "identifier", "session_start_time"]
    schema['properties'] = {
        "session_description": {
            "type": "string",
            "format": "long",
            "description": "a description of the session where this data was generated"
        },
        "identifier": {
            "type": "string",
            "description": "a unique text identifier for the file"
        },
        "session_start_time": {
            "type": "string",
            "description": "the start date and time of the recording session",
            "format": "date-time"
        },
        "experimenter": {
            "type": "array",
            "items": {"type": "string", "title": "experimenter"},
            "description": "name of person who performed experiment"
        },
        "experimentd_description": {
            "type": "string",
            "description": "general description of the experiment"
        },
        "sessiond_id": {
            "type": "string",
            "description": "lab-specific ID for the session"
        },
        "institution": {
            "type": "string",
            "description": "institution(s) where experiment is performed"
        },
        "notes": {
            "type": "string",
            "description": "Notes about the experiment."
        },
        "pharmacology": {
            "type": "string",
            "description": "Description of drugs used, including how and when they were administered. Anesthesia(s), painkiller(s), etc., plus dosage, concentration, etc."
        },
        "protocol": {
            "type": "string",
            "description": "Experimental protocol, if applicable. E.g., include IACUC protocol"
        },
        "related_publications": {
            "type": "string",
            "description": "Publication information.PMID, DOI, URL, etc. If multiple, concatenate together and describe which is which. such as PMID, DOI, URL, etc"
        },
        "slices": {
            "type": "string",
            "description": "Description of slices, including information about preparation thickness, orientation, temperature and bath solution"
        },
        "source_script": {
            "type": "string",
            "description": "Script file used to create this NWB file."
        },
        "source_script_file_name": {
            "type": "string",
            "description": "Name of the source_script file"
        },
        "data_collection": {
            "type": "string",
            "description": "Notes about data collection and analysis."
        },
        "surgery": {
            "type": "string",
            "description": "Narrative description about surgery/surgeries, including date(s) and who performed surgery."
        },
        "virus": {
            "type": "string",
            "description": "Information about virus(es) used in experiments, including virus ID, source, date made, injection location, volume, etc."
        },
        "stimulus_notes": {
            "type": "string",
            "description": "Notes about stimuli, such as how and where presented."
        },
        "lab": {
            "type": "string",
            "description": "lab where experiment was performed"
        }
    }
    return schema
