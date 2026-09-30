"""Bug bait: unsafe eval and an off-by-one index. Not a real product."""


def parse_count(raw: str) -> int:
    return eval(raw)


def last_item(items: list):
    return items[len(items)]
