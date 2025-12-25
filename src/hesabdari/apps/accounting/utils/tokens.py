import time

TOKEN_TTL = 30 * 60  # token expiration = 30 minutes


def get_tokens(session):
    """
    get tokens from session and remove
    expired tokens
    output: {token: timestamp}
    """
    now = time.time()
    tokens = session.get("form_tokens", {})
    # keep the live tokens
    tokens = {t: ts for t, ts in tokens.items() if now - ts < TOKEN_TTL}
    session["form_tokens"] = tokens
    return tokens