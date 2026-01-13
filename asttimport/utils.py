def clean_id(base: str) -> str:
    return base.replace(".", "-").replace(" ", "-").replace("/", "-")