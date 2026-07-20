# API calls in library: None
# Discovered from: run_exploit.sh
# Target package: None
# Total unique API calls: 4

# API ID: 1
# Found in versions: None
# API: keras.layers.Input
# Call chain: None
keras.layers.Input(shape=[{'type': 'literal', 'value': 10}], name='input')

# API ID: 2
# Found in versions: None
# API: keras.layers.TFSMLayer
# Call chain: None
keras.layers.TFSMLayer(savedmodel_path, call_endpoint='serving_default')

# API ID: 3
# Found in versions: None
# API: keras.models.Model
# Call chain: None
keras.models.Model(inputs=input_layer, outputs=output)

# API ID: 4
# Found in versions: None
# API: keras.models.load_model
# Call chain: None
keras.models.load_model('malicious_model.keras', safe_mode=True)

