"""Parse sync job specifications."""


def parse_job_spec(raw: str) -> dict[str, str]:
    job: dict[str, str] = {}
    for part in raw.split(";"):
        item = part.strip()
        if not item:
            continue
        key, value = item.split("=", 1)
        job[key.strip()] = value.strip()

    required = {"name", "path", "mode"}
    missing = sorted(required - set(job))
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    return job
