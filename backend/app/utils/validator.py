def clamp(value: int, minimum: int, maximum: int) -> int:
    return min(max(value, minimum), maximum)
