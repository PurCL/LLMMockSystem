# API calls in library: tree
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 2

# API ID: 1
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5
# API: tree.flatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.backend.torch.core.convert_to_tensor -> tree.flatten
tree.flatten(x)

# API ID: 2
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5
# API: tree.flatten
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.utils.file_utils.copy -> keras.src.utils.module_utils.gfile.copy -> keras.src.backend.any_symbolic_tensors -> tree.flatten
tree.flatten([{'type': 'variable', 'value': 'args'}, {'type': 'variable', 'value': 'kwargs'}])
