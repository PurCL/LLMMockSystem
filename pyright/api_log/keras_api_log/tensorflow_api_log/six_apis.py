# API calls in library: six
# Discovered from: tensorflow_apis.py
# Target package: tensorflow
# Total unique API calls: 2

# API ID: 1
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1
# API: six.get_method_self
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.cond_v2.cond_v2 -> tensorflow.python.framework.func_graph.func_graph_from_py_func -> tensorflow.python.util.function_utils.get_func_name -> six.get_method_self
six.get_method_self(func)

# API ID: 2
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1
# API: six.get_method_function
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.ops.cond.cond -> tensorflow.python.ops.cond_v2.cond_v2 -> tensorflow.python.framework.func_graph.func_graph_from_py_func -> tensorflow.python.util.function_utils.get_func_name -> six.get_method_function
six.get_method_function(func)
