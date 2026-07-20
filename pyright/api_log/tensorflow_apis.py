# API calls in library: None
# Discovered from: run_exploit.sh
# Target package: None
# Total unique API calls: 15

# API ID: 1
# Found in versions: None
# API: tensorflow.TensorSpec
# Call chain: None
tensorflow.TensorSpec(shape=[{'type': 'literal', 'value': None}, {'type': 'literal', 'value': 10}], dtype=tf.float32)

# API ID: 2
# Found in versions: None
# API: tensorflow.Variable
# Call chain: None
tensorflow.Variable(0, dtype=tf.int32)

# API ID: 3
# Found in versions: None
# API: tensorflow.constant
# Call chain: None
tensorflow.constant('EXPLOIT_SUCCESSFUL: CVE-2026-1462 vulnerability confirmed!\nAttacker-controlled SavedModel was loaded despite safe_mode=True\nThis demonstrates arbitrary code execution capability.\n')

# API ID: 4
# Found in versions: None
# API: tensorflow.constant
# Call chain: None
tensorflow.constant('STOLEN_DATA:\n')

# API ID: 5
# Found in versions: None
# API: tensorflow.constant
# Call chain: None
tensorflow.constant('\nVICTIM_SESSION_TOKEN=abc123xyz789\n')

# API ID: 6
# Found in versions: None
# API: tensorflow.constant
# Call chain: None
tensorflow.constant('VICTIM_API_ENDPOINT=https://victim.internal.api/\n')

# API ID: 7
# Found in versions: None
# API: tensorflow.constant
# Call chain: None
tensorflow.constant(np.random.randn(1, 10).astype(...))

# API ID: 8
# Found in versions: None
# API: tensorflow.function
# Call chain: None
tensorflow.function(input_signature=[{'type': 'expression', 'value': 'tf.TensorSpec(...)'}])

# API ID: 9
# Found in versions: None
# API: tensorflow.io.read_file
# Call chain: None
tensorflow.io.read_file('attacker_payload.txt')

# API ID: 10
# Found in versions: None
# API: tensorflow.io.write_file
# Call chain: None
tensorflow.io.write_file('exploit_marker.txt', exploit_msg)

# API ID: 11
# Found in versions: None
# API: tensorflow.io.write_file
# Call chain: None
tensorflow.io.write_file('victim_data.txt', victim_msg)

# API ID: 12
# Found in versions: None
# API: tensorflow.reduce_mean
# Call chain: None
tensorflow.reduce_mean(x, axis=-1, keepdims=True)

# API ID: 13
# Found in versions: None
# API: tensorflow.saved_model.load
# Call chain: None
tensorflow.saved_model.load(savedmodel_path)

# API ID: 14
# Found in versions: None
# API: tensorflow.saved_model.save
# Call chain: None
tensorflow.saved_model.save(malicious_module, savedmodel_path, signatures={'serving_default': {'type': 'variable', 'value': 'concrete_func'}})

# API ID: 15
# Found in versions: None
# API: tensorflow.strings.join
# Call chain: None
tensorflow.strings.join([{'type': 'expression', 'value': 'tf.constant(...)'}, {'type': 'variable', 'value': 'payload_content'}, {'type': 'expression', 'value': 'tf.constant(...)'}, {'type': 'expression', 'value': 'tf.constant(...)'}])

