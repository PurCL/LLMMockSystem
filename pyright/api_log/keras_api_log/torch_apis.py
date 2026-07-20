# API calls in library: torch
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 13

# API ID: 1
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: torch.as_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.as_tensor
torch.as_tensor(x, dtype=torch.bool, device=get_device(...))

# API ID: 2
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: torch.as_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.as_tensor
torch.as_tensor(x, dtype=torch.int32, device=get_device(...))

# API ID: 3
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: torch.as_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.as_tensor
torch.as_tensor(x, dtype=to_torch_dtype(...), device=get_device(...))

# API ID: 4
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: torch.as_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.as_tensor
torch.as_tensor(x, dtype=dtype, device=get_device(...))

# API ID: 5
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: torch.stack
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.stack
torch.stack([convert_to_tensor(x1) for x1 in x])

# API ID: 6
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: torch.clone
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> torch.clone
torch.clone(x)

# API ID: 7
# Found in versions: 3.1.0, 3.1.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: torch.reshape
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.utils.tree.flatten -> keras.src.utils.module_utils.tensorflow.reshape -> torch.reshape
torch.reshape(x, newshape)

# API ID: 8
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0
# API: torch.empty_like
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.empty_like
torch.empty_like(x, device=device)

# API ID: 9
# Found in versions: 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0
# API: torch.utils._pytree.tree_flatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.backend.common.standardize_dtype -> keras.src.backend.common.dtypes.PYTHON_DTYPES_MAP.get -> keras.src.dtype_policies.dtype_policy.dtype_policy -> keras.src.dtype_policies.get -> keras.src.saving.serialization_lib.deserialize_keras_object -> keras.src.backend.convert_to_tensor -> keras.src.tree.flatten -> torch.utils._pytree.tree_flatten
torch.utils._pytree.tree_flatten(structure)

# API ID: 10
# Found in versions: 3.14.0, 3.14.1
# API: torch.as_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.as_tensor
torch.as_tensor(x, dtype=torch.int64, device=get_device(...))

# API ID: 11
# Found in versions: 3.15.0
# API: torch.as_tensor
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> torch.as_tensor
torch.as_tensor(x, dtype=dt, device=get_device(...))

# API ID: 12
# Found in versions: 3.15.0
# API: torch.utils._pytree.tree_flatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.dmtree.traverse -> keras.src.tree.dmtree_impl.traverse -> torch.utils._pytree.tree_flatten
torch.utils._pytree.tree_flatten(structure, is_leaf=lambda x: x is not structure)

# API ID: 13
# Found in versions: 3.15.0
# API: torch.utils._pytree.tree_unflatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.dmtree.traverse -> keras.src.tree.dmtree_impl.traverse -> torch.utils._pytree.tree_unflatten
torch.utils._pytree.tree_unflatten([traverse(func, c, top_down=top_down) for c in children], treedef)
