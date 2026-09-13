import uuid

def random_email() -> str:
    return f"test_{uuid.uuid4().hex[:6]}@example.com"
