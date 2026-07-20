# API calls in library: h5py
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 1

# API ID: 1
# Found in versions: 3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.0.4, 3.0.5, 3.1.0, 3.1.1, 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.2.0, 3.2.1, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.4.0, 3.4.1, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: h5py.File
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.saving.saving_lib.load_model -> keras.src.legacy.saving.legacy_h5_format.load_model_from_hdf5 -> h5py.File
h5py.File(filepath, mode='r')
