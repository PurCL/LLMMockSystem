# API calls in library: numpy
# Discovered from: tensorflow_apis.py
# Target package: tensorflow
# Total unique API calls: 26

# API ID: 1
# Found in versions: 2.12.0, 2.12.0rc0, 2.12.0rc1, 2.12.1, 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.dtype
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.linalg.sparse.gen_sparse_csr_matrix_ops.sparse_matrix_transpose -> tensorflow.python.eager.execute.make_type -> tensorflow.python.framework.dtypes.as_dtype -> numpy.dtype
numpy.dtype(type_value.dtype)

# API ID: 2
# Found in versions: 2.12.0, 2.12.0rc0, 2.12.0rc1, 2.12.1, 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.arange
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> numpy.arange
numpy.arange(rank - 1, -1, -1, dtype=np.int32)

# API ID: 3
# Found in versions: 2.12.0, 2.12.0rc0, 2.12.0rc1, 2.12.1, 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.zeros
# Call chain: tensorflow.sparse.to_dense -> tensorflow.sparse.to_dense -> tensorflow.python.ops.sparse_ops.sparse_tensor_to_dense -> tensorflow.python.ops.array_ops.zeros -> numpy.zeros
numpy.zeros([])

# API ID: 4
# Found in versions: 2.12.0, 2.12.0rc0, 2.12.0rc1, 2.12.1, 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.asarray
# Call chain: tensorflow.sparse.to_dense -> tensorflow.sparse.to_dense -> tensorflow.python.ops.sparse_ops.sparse_tensor_to_dense -> tensorflow.python.ops.array_ops.zeros -> tensorflow.python.ops.numpy_ops.np_utils.result_type -> numpy.asarray
numpy.asarray([])

# API ID: 5
# Found in versions: 2.12.0, 2.12.0rc0, 2.12.0rc1, 2.12.1, 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.float32
# Call chain: tensorflow.sparse.to_dense -> tensorflow.sparse.to_dense -> tensorflow.python.ops.sparse_ops.sparse_tensor_to_dense -> tensorflow.python.ops.array_ops.zeros -> tensorflow.python.ops.numpy_ops.np_utils.result_type -> tensorflow.python.ops.numpy_ops.np_dtypes._result_type -> numpy.float32
numpy.float32(x)

# API ID: 6
# Found in versions: 2.12.0, 2.12.0rc0, 2.12.0rc1, 2.12.1, 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.complex64
# Call chain: tensorflow.sparse.to_dense -> tensorflow.sparse.to_dense -> tensorflow.python.ops.sparse_ops.sparse_tensor_to_dense -> tensorflow.python.ops.array_ops.zeros -> tensorflow.python.ops.numpy_ops.np_utils.result_type -> tensorflow.python.ops.numpy_ops.np_dtypes._result_type -> numpy.complex64
numpy.complex64(x)

# API ID: 7
# Found in versions: 2.12.0, 2.12.0rc0, 2.12.0rc1, 2.12.1, 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.result_type
# Call chain: tensorflow.sparse.to_dense -> tensorflow.sparse.to_dense -> tensorflow.python.ops.sparse_ops.sparse_tensor_to_dense -> tensorflow.python.ops.array_ops.zeros -> tensorflow.python.ops.numpy_ops.np_utils.result_type -> tensorflow.python.ops.numpy_ops.np_dtypes._result_type -> numpy.result_type
numpy.result_type(*arrays_and_dtypes)

# API ID: 8
# Found in versions: 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.array
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.gen_array_ops.reshape -> tensorflow.python.ops.shape_util.maybe_set_static_shape -> tensorflow.python.framework.tensor_util.constant_value_as_shape -> numpy.array
numpy.array([x if x is not None else -1 for x in pre_cast.as_list()])

# API ID: 9
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.array
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> numpy.array
numpy.array(row_splits, dtype=row_splits_dtype)

# API ID: 10
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.array
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> numpy.array
numpy.array(pylist, dtype=dtype)

# API ID: 11
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.array
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.ops.gen_array_ops.pack -> tensorflow.dtensor.python.api.pack -> tensorflow.python.ops.array_ops.split -> tensorflow.python.ops.array_ops.repeat -> numpy.array
numpy.array(repeats)

# API ID: 12
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1
# API: numpy.reshape
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> numpy.reshape
numpy.reshape(np.array(...), shape)

# API ID: 13
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.ndarray
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> numpy.ndarray
numpy.ndarray([0] + self._element_shape)

# API ID: 14
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.prod
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.ops.gen_array_ops.pack -> tensorflow.dtensor.python.api.pack -> tensorflow.python.ops.array_ops.size -> numpy.prod
numpy.prod(x.shape.as_list(...), dtype=int)

# API ID: 15
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.prod
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.ops.gen_array_ops.pack -> tensorflow.dtensor.python.api.pack -> tensorflow.python.ops.array_ops.split -> tensorflow.python.ops.array_ops.repeat -> numpy.prod
numpy.prod(original_shape)

# API ID: 16
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.cumprod
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.ops.gen_array_ops.pack -> tensorflow.dtensor.python.api.pack -> tensorflow.python.ops.array_ops.split -> tensorflow.python.ops.ragged.dynamic_ragged_shape.DynamicRaggedShape.from_tensor -> numpy.cumprod
numpy.cumprod(input_shape)

# API ID: 17
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.ravel
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.ops.gen_array_ops.pack -> tensorflow.dtensor.python.api.pack -> tensorflow.python.ops.array_ops.split -> tensorflow.python.ops.array_ops.repeat -> numpy.ravel
numpy.ravel(np.array(...))

# API ID: 18
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.ones
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.ones_like -> tensorflow.python.ops.array_ops.ones -> numpy.ones
numpy.ones([])

# API ID: 19
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.ndim
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.tile -> tensorflow.python.ops.array_ops.pad -> numpy.ndim
numpy.ndim(constant_values)

# API ID: 20
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.zeros_like
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.tile -> tensorflow.python.ops.array_ops.pad -> numpy.zeros_like
numpy.zeros_like(constant_values)

# API ID: 21
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.isscalar
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.tile -> tensorflow.python.ops.math_ops.maximum -> tensorflow.python.ops.math_ops.logical_or -> numpy.isscalar
numpy.isscalar(a_value)

# API ID: 22
# Found in versions: 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.asarray
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> tensorflow.python.util.numpy_compat.np_reshape -> numpy.asarray
numpy.asarray(a, order=order, copy=copy)

# API ID: 23
# Found in versions: 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.array
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> numpy.array
numpy.array(pylist)

# API ID: 24
# Found in versions: 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.lib.NumpyVersion
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> tensorflow.python.util.numpy_compat.np_reshape -> numpy.lib.NumpyVersion
numpy.lib.NumpyVersion(np.__version__)

# API ID: 25
# Found in versions: 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.reshape
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> tensorflow.python.util.numpy_compat.np_reshape -> numpy.reshape
numpy.reshape(a, shape, order=order, copy=copy)

# API ID: 26
# Found in versions: 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: numpy.reshape
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.control_flow_ops.switch -> tensorflow.python.ops.array_ops.concat -> tensorflow.python.ops.array_ops_stack.stack -> tensorflow.python.framework.tensor_util.constant_value -> tensorflow.python.util.numpy_compat.np_reshape -> numpy.reshape
numpy.reshape(a, shape, order=order)
