"""Bridge captured provider identities into the existing GUI/engine FileSource API."""
from equipment_data_manager.storage.contracts import StorageError


class ProviderFileSource:
    def __init__(self, provider, selections):
        self.provider, self.selections = provider, dict(selections)

    def read(self, source):
        entry = self.selections.get(source.reference)
        if entry is None or entry.name != source.name:
            raise StorageError('storage_reference_rejected')
        return self.provider.read(entry).content
