from uuid import UUID


def format_size_bytes(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def professional_name(professional) -> str:
    return professional.name if professional else ""


def parse_uuid(value: str) -> UUID:
    return UUID(value)
