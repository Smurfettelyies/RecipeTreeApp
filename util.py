# Helper file

def match_string(query: str, target: str) -> bool:
    """True if query is a substring of target (case-insensitive)."""
    return query.strip().lower() in target.strip().lower()

def match_exact(query: str, target: str) -> bool:
    """True if query equals target (case-insensitive)."""
    return query.strip().lower() == target.strip().lower()

def format_stack(name: str, amount: int) -> str:
    """'Iron Ingot' + 4 → 'Iron Ingot x4', amount 1 → 'Iron Ingot'"""
    return f"{name} x{amount}" if amount > 1 else name

def parse_amount(text: str) -> int:
    """'4' → 4, '' oder ungültig → 1"""
    try:
        v = int(text.strip())
        return v if v > 0 else 1
    except ValueError:
        return 1

def capitalize_name(name: str) -> str:
    return name.strip().title()