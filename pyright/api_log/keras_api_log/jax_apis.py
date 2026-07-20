# API calls in library: jax
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 9

# API ID: 1
# Found in versions: 3.0.0, 3.0.1, 3.0.2
# API: jax.numpy.array
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> jax.numpy.array
jax.numpy.array(x, dtype=dtype)

# API ID: 2
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: jax.numpy.copy
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> jax.numpy.copy
jax.numpy.copy(x)

# API ID: 3
# Found in versions: 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: jax.numpy.asarray
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> jax.numpy.asarray
jax.numpy.asarray(x, dtype=dtype)

# API ID: 4
# Found in versions: 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: jax.numpy.asarray
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> jax.numpy.asarray
jax.numpy.asarray(x)

# API ID: 5
# Found in versions: 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: jax.experimental.sparse.bcoo_sum_duplicates
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.jax.sparse.elementwise_unary -> jax.experimental.sparse.bcoo_sum_duplicates
jax.experimental.sparse.bcoo_sum_duplicates(x)

# API ID: 6
# Found in versions: 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: jax.experimental.sparse.BCOO
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.jax.sparse.elementwise_unary -> jax.experimental.sparse.BCOO
jax.experimental.sparse.BCOO([{'type': 'expression', 'value': 'func(...)'}, {'type': 'expression', 'value': 'x.indices'}], shape=x.shape)

# API ID: 7
# Found in versions: 3.1.0, 3.1.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: jax.experimental.sparse.bcoo_reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.utils.tree.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> jax.experimental.sparse.bcoo_reshape
jax.experimental.sparse.bcoo_reshape(x, new_sizes=newshape)

# API ID: 8
# Found in versions: 3.1.0, 3.1.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: jax.numpy.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.utils.tree.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> jax.numpy.reshape
jax.numpy.reshape(x, newshape)

# API ID: 9
# Found in versions: 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0
# API: jax.export.is_symbolic_dim
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.backend.standardize_shape -> jax.export.is_symbolic_dim
jax.export.is_symbolic_dim(d)
