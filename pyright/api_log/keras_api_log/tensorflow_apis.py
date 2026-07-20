# API calls in library: tensorflow
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 14

# API ID: 1
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.2.0, 3.2.1
# API: tensorflow.sparse.to_dense
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> tensorflow.sparse.to_dense
tensorflow.sparse.to_dense(x)

# API ID: 2
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.is_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> tensorflow.is_tensor
tensorflow.is_tensor(x)

# API ID: 3
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.convert_to_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> tensorflow.convert_to_tensor
tensorflow.convert_to_tensor(x)

# API ID: 4
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.convert_to_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> tensorflow.convert_to_tensor
tensorflow.convert_to_tensor(x, dtype=dtype)

# API ID: 5
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.cast
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> tensorflow.cast
tensorflow.cast(x, dtype)

# API ID: 6
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.cast
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> tensorflow.cast
tensorflow.cast(x, dtype=dtype)

# API ID: 7
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.2.0, 3.2.1
# API: tensorflow.experimental.numpy.copy
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> tensorflow.experimental.numpy.copy
tensorflow.experimental.numpy.copy(x)

# API ID: 8
# Found in versions: 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.IndexedSlices
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.jax.sparse.elementwise_unary -> tensorflow.IndexedSlices
tensorflow.IndexedSlices(func(...), x.indices, x.dense_shape)

# API ID: 9
# Found in versions: 3.1.0, 3.1.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.sparse.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.utils.tree.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> tensorflow.sparse.reshape
tensorflow.sparse.reshape(x, newshape)

# API ID: 10
# Found in versions: 3.1.0, 3.1.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.utils.tree.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> tensorflow.reshape
tensorflow.reshape(x, newshape)

# API ID: 11
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.constant
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> keras.src.backend.tensorflow.sparse.sparse_to_dense -> tensorflow.constant
tensorflow.constant(default_value, dtype=x.dtype)

# API ID: 12
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> keras.src.backend.tensorflow.sparse.sparse_to_dense -> tensorflow.reshape
tensorflow.reshape(x.values, [])

# API ID: 13
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.sparse.to_dense
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> keras.src.backend.tensorflow.sparse.sparse_to_dense -> tensorflow.sparse.to_dense
tensorflow.sparse.to_dense(x, default_value=default_value)

# API ID: 14
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: tensorflow.identity
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> tensorflow.identity
tensorflow.identity(x)
