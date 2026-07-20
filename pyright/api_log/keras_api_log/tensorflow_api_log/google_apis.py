# API calls in library: google
# Discovered from: tensorflow_apis.py
# Target package: tensorflow
# Total unique API calls: 5

# API ID: 1
# Found in versions: 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1
# API: google.protobuf.text_format.Merge
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.framework.ops.convert_to_tensor -> tensorflow.python.framework.tensor_conversion_registry.convert -> tensorflow.lite.python.convert_saved_model.freeze_saved_model -> tensorflow.python.saved_model.loader.load -> tensorflow.python.saved_model.loader_impl.parse_saved_model -> google.protobuf.text_format.Merge
google.protobuf.text_format.Merge(file_content.decode(...), saved_model)

# API ID: 2
# Found in versions: 2.13.0, 2.13.0rc0, 2.13.0rc1, 2.13.0rc2, 2.13.1, 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0
# API: google.protobuf.text_format.MessageToString
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.framework.ops.convert_to_tensor -> tensorflow.python.framework.tensor_conversion_registry.convert -> tensorflow.python.training.saver.export_meta_graph -> tensorflow.python.framework.meta_graph.export_scoped_meta_graph -> tensorflow.python.framework.graph_io.write_graph -> google.protobuf.text_format.MessageToString
google.protobuf.text_format.MessageToString(graph_def, float_format='')

# API ID: 3
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1, 2.16.0rc0, 2.16.1, 2.16.2, 2.17.0, 2.17.0rc0, 2.17.0rc1, 2.17.1, 2.18.0, 2.18.0rc0, 2.18.0rc1, 2.18.0rc2, 2.18.1, 2.19.0, 2.19.0rc0, 2.19.1, 2.20.0, 2.20.0rc0, 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: google.protobuf.text_format.Parse
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.framework.ops.convert_to_tensor -> tensorflow.python.framework.tensor_conversion_registry.convert -> tensorflow.lite.python.convert_saved_model.freeze_saved_model -> tensorflow.python.saved_model.loader.load -> tensorflow.python.saved_model.loader_impl.parse_saved_model -> google.protobuf.text_format.Parse
google.protobuf.text_format.Parse(file_content.decode(...), saved_model)

# API ID: 4
# Found in versions: 2.14.0, 2.14.0rc0, 2.14.0rc1, 2.14.1, 2.15.0, 2.15.0.post1, 2.15.0rc0, 2.15.0rc1, 2.15.1
# API: google.protobuf.text_format.ParseLines
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.framework.ops.convert_to_tensor -> tensorflow.python.framework.tensor_conversion_registry.convert -> tensorflow.lite.python.convert_saved_model.freeze_saved_model -> tensorflow.python.saved_model.loader.load -> tensorflow.python.saved_model.load.load -> tensorflow.python.saved_model.load.load_partial -> tensorflow.python.saved_model.load_v1_in_v2.load -> tensorflow.python.data.ops.load_op._load -> google.protobuf.text_format.ParseLines
google.protobuf.text_format.ParseLines(f, snapshot_pb2.DistributedSnapshotMetadata(...))

# API ID: 5
# Found in versions: 2.21.0, 2.21.0rc0, 2.21.0rc1
# API: google.protobuf.text_format.MessageToString
# Call chain: tensorflow.sparse.reshape -> tensorflow.sparse.reshape -> tensorflow.python.ops.array_ops.transpose -> tensorflow.python.framework.ops.convert_to_tensor -> tensorflow.python.framework.tensor_conversion_registry.convert -> tensorflow.python.training.saver.export_meta_graph -> tensorflow.python.framework.meta_graph.export_scoped_meta_graph -> tensorflow.python.framework.graph_io.write_graph -> google.protobuf.text_format.MessageToString
google.protobuf.text_format.MessageToString(graph_def)
