def to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).lower() in {'1', 'true', 'yes', 'y', 'on'}


