# API calls in library: openvino
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 29

# API ID: 1
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.runtime.opset14.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> openvino.runtime.opset14.constant
openvino.runtime.opset14.constant(x, ov_type)

# API ID: 2
# Found in versions: 3.10.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.runtime.opset14.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> openvino.runtime.opset14.constant
openvino.runtime.opset14.constant(x)

# API ID: 3
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.Tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> openvino.Tensor
openvino.Tensor(np.asarray(x).astype(...))

# API ID: 4
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.Tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> openvino.Tensor
openvino.Tensor(np.array(...))

# API ID: 5
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.runtime.opset14.convert
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.ops.cast -> keras.src.backend.torch.core.cast -> openvino.runtime.opset14.convert
openvino.runtime.opset14.convert(x, ov_type)

# API ID: 6
# Found in versions: 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2
# API: openvino.opset14.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> openvino.opset14.constant
openvino.opset14.constant(x, ov_type)

# API ID: 7
# Found in versions: 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2
# API: openvino.opset14.convert
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.ops.cast -> keras.src.backend.torch.core.cast -> openvino.opset14.convert
openvino.opset14.convert(x, ov_type)

# API ID: 8
# Found in versions: 3.14.0, 3.14.1
# API: openvino.opset15.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> openvino.opset15.constant
openvino.opset15.constant(x, ov_type)

# API ID: 9
# Found in versions: 3.14.0, 3.14.1
# API: openvino.opset15.convert
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.ops.cast -> keras.src.backend.torch.core.cast -> openvino.opset15.convert
openvino.opset15.convert(x, ov_type)

# API ID: 10
# Found in versions: 3.15.0
# API: openvino.opset16.convert
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.tensorflow.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.ops.cast -> openvino.opset16.convert
openvino.opset16.convert(x, ov_type)

# API ID: 11
# Found in versions: 3.15.0
# API: openvino.opset16.convert
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.opset16.convert
openvino.opset16.convert(x, Type.bf16)

# API ID: 12
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.tensorflow.core.convert_to_tensor -> openvino.opset16.constant
openvino.opset16.constant(x, ov_type)

# API ID: 13
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.opset16.constant
openvino.opset16.constant(x, Type.f32)

# API ID: 14
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.opset16.constant
openvino.opset16.constant(float(...), Type.f32)

# API ID: 15
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.opset16.constant
openvino.opset16.constant(x, OPENVINO_DTYPES['bfloat16'])

# API ID: 16
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.opset16.constant
openvino.opset16.constant(x)

# API ID: 17
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.opset16.constant
openvino.opset16.constant(x.value.data)

# API ID: 18
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.opset16.constant
openvino.opset16.constant(x.data)

# API ID: 19
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.opset16.constant
openvino.opset16.constant(0, Type.i32)

# API ID: 20
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.opset16.constant
openvino.opset16.constant([{'type': 'variable', 'value': 'val'}], Type.i32)

# API ID: 21
# Found in versions: 3.15.0
# API: openvino.opset16.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.opset16.constant
openvino.opset16.constant(newshape, Type.i32)

# API ID: 22
# Found in versions: 3.15.0
# API: openvino.opset16.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.opset16.reshape
openvino.opset16.reshape(first, shape_const, False)

# API ID: 23
# Found in versions: 3.15.0
# API: openvino.opset16.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.opset16.reshape
openvino.opset16.reshape(x, newshape, False)

# API ID: 24
# Found in versions: 3.15.0
# API: openvino.opset16.unsqueeze
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.opset16.unsqueeze
openvino.opset16.unsqueeze(d_ov, axis)

# API ID: 25
# Found in versions: 3.15.0
# API: openvino.opset16.concat
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.opset16.concat
openvino.opset16.concat(dim_tensors, 0)

# API ID: 26
# Found in versions: 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.runtime.opset14.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.runtime.opset14.constant
openvino.runtime.opset14.constant(x.value.data)

# API ID: 27
# Found in versions: 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.runtime.opset14.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> keras.src.backend.openvino.core.get_ov_output -> openvino.runtime.opset14.constant
openvino.runtime.opset14.constant(x.data)

# API ID: 28
# Found in versions: 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.runtime.opset14.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.runtime.opset14.constant
openvino.runtime.opset14.constant(newshape, Type.i32)

# API ID: 29
# Found in versions: 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: openvino.runtime.opset14.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> openvino.runtime.opset14.reshape
openvino.runtime.opset14.reshape(x, newshape, False)
