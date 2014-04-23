_settings = None

def get_settings():
    global _settings
    if _settings is None:
        _settings = {}
    return _settings
