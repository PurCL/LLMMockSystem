# API calls in library: optree
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 4

# API ID: 1
# Found in versions: 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: optree.tree_flatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.utils.tree.flatten -> optree.tree_flatten
optree.tree_flatten(structure, none_is_leaf=True, namespace='keras')

# API ID: 2
# Found in versions: 3.15.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: optree.tree_is_leaf
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.is_nested -> keras.src.utils.module_utils.dmtree.is_nested -> optree.tree_is_leaf
optree.tree_is_leaf(structure, none_is_leaf=True, namespace='keras')

# API ID: 3
# Found in versions: 3.15.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: optree.tree_flatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.dmtree.traverse -> keras.src.tree.dmtree_impl.traverse -> optree.tree_flatten
optree.tree_flatten(structure, is_leaf=lambda x: x is not structure, none_is_leaf=True, namespace='keras')

# API ID: 4
# Found in versions: 3.15.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: optree.tree_unflatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> keras.src.tree.flatten -> keras.src.tree.dmtree_impl.flatten -> keras.src.utils.module_utils.dmtree.traverse -> keras.src.tree.dmtree_impl.traverse -> optree.tree_unflatten
optree.tree_unflatten(treedef, [traverse(func, c, top_down=top_down) for c in children])
