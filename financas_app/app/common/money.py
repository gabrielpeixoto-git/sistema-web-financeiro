def parse_brl_to_cents(s: str) -> int:
    s = (s or "").strip()
    if not s:
        raise ValueError("empty amount")
    s = s.replace(".", "").replace(",", ".")
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    if "." in s:
        whole, frac = s.split(".", 1)
        frac = (frac + "00")[:2]
    else:
        whole, frac = s, "00"
    cents = int(whole or "0") * 100 + int(frac)
    return -cents if neg else cents


def cents_to_brl(cents: int) -> str:
    neg = cents < 0
    cents = abs(int(cents))
    whole, frac = divmod(cents, 100)
    s = f"{whole:,}".replace(",", ".") + f",{frac:02d}"
    return f"-{s}" if neg else s

