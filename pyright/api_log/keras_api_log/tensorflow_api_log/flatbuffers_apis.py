# API calls in library: flatbuffers
# Discovered from: tensorflow_apis.py
# Target package: tensorflow
# Total unique API calls: 1

# API ID: 1
# Found in versions: 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: flatbuffers.number_types.UOffsetTFlags.py_type
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.gen_array_ops.reshape -> tensorflow.python.ops.shape_util.maybe_set_static_shape -> tensorflow.python.framework.tensor_util.constant_value_as_shape -> tensorflow.python.framework.tensor_shape.Dimension -> flatbuffers.number_types.UOffsetTFlags.py_type
flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(...))
