# API calls in library: huggingface_hub
# Discovered from: keras_apis.py
# Target package: keras
# Total unique API calls: 1

# API ID: 1
# Found in versions: 3.10.0, 3.11.0, 3.11.1, 3.11.2, 3.11.3, 3.12.0, 3.12.1, 3.12.2, 3.12.3, 3.13.0, 3.13.1, 3.13.2, 3.14.0, 3.14.1, 3.15.0, 3.5.0, 3.6.0, 3.7.0, 3.8.0, 3.9.0, 3.9.1, 3.9.2
# API: huggingface_hub.snapshot_download
# Call chain: keras.models.load_model -> keras.models.load_model -> keras.src.saving.saving_lib.load_model -> huggingface_hub.snapshot_download
huggingface_hub.snapshot_download(repo_id=repo_id, library_name='keras', library_version=keras_version)
