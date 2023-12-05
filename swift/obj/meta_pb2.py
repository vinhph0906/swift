# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: meta.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='meta.proto',
  package='meta',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=b'\n\nmeta.proto\x12\x04meta\"\"\n\x04\x41ttr\x12\x0b\n\x03key\x18\x01 \x01(\x0c\x12\r\n\x05value\x18\x02 \x01(\x0c\"%\n\x08Metadata\x12\x19\n\x05\x61ttrs\x18\x01 \x03(\x0b\x32\n.meta.Attrb\x06proto3'
)




_ATTR = _descriptor.Descriptor(
  name='Attr',
  full_name='meta.Attr',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='meta.Attr.key', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='value', full_name='meta.Attr.value', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=20,
  serialized_end=54,
)


_METADATA = _descriptor.Descriptor(
  name='Metadata',
  full_name='meta.Metadata',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='attrs', full_name='meta.Metadata.attrs', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=56,
  serialized_end=93,
)

_METADATA.fields_by_name['attrs'].message_type = _ATTR
DESCRIPTOR.message_types_by_name['Attr'] = _ATTR
DESCRIPTOR.message_types_by_name['Metadata'] = _METADATA
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Attr = _reflection.GeneratedProtocolMessageType('Attr', (_message.Message,), {
  'DESCRIPTOR' : _ATTR,
  '__module__' : 'meta_pb2'
  # @@protoc_insertion_point(class_scope:meta.Attr)
  })
_sym_db.RegisterMessage(Attr)

Metadata = _reflection.GeneratedProtocolMessageType('Metadata', (_message.Message,), {
  'DESCRIPTOR' : _METADATA,
  '__module__' : 'meta_pb2'
  # @@protoc_insertion_point(class_scope:meta.Metadata)
  })
_sym_db.RegisterMessage(Metadata)


# @@protoc_insertion_point(module_scope)
