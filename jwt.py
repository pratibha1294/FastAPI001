import importlib.machinery
import importlib.util
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def _load_pyjwt():
    """Load the installed `pyjwt` package, bypassing this file's own
    name collision with it (both import as `jwt`)."""
    local_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths = [p for p in sys.path if os.path.abspath(p or os.getcwd()) != local_dir]
    spec = importlib.machinery.PathFinder.find_spec("jwt", search_paths)
    if spec is None or spec.loader is None:
        raise ImportError("pyjwt package not found; install it with `uv add pyjwt`")
    module = importlib.util.module_from_spec(spec)

    # pyjwt's own submodules use relative imports (e.g. `from .api_jwk import
    # ...`), which requires sys.modules["jwt"] to point at it while it loads.
    # That key is already claimed by this file, so swap it in temporarily.
    previous = sys.modules.get("jwt")
    sys.modules["jwt"] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is not None:
            sys.modules["jwt"] = previous
        else:
            sys.modules.pop("jwt", None)
        for name in list(sys.modules):
            if name.startswith("jwt."):
                del sys.modules[name]

    return module


_pyjwt = _load_pyjwt()

DEFAULT_SECRET = "changeme"
DEFAULT_ALGORITHM = "HS256"
DEFAULT_EXPIRY_SECONDS = 3600


class TokenError(Exception):
    """Base class for all token-related errors."""


class TokenIsExpiredError(TokenError):
    """Raised when a JWT's `exp` claim is in the past."""


class TokenIsInvalidError(TokenError):
    """Raised when a JWT is malformed, has a bad signature, or fails other validation."""


@dataclass
class TokenData:
    sub: str
    iat: datetime
    exp: datetime
    claims: dict[str, Any] = field(default_factory=dict)


def create(
    sub: str,
    claims: Optional[dict[str, Any]] = None,
    exp: Optional[datetime] = None,
    secret: str = DEFAULT_SECRET,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    now = datetime.now(timezone.utc)
    if exp is None:
        exp = now + timedelta(seconds=DEFAULT_EXPIRY_SECONDS)

    payload: dict[str, Any] = {"sub": sub, "iat": now, "exp": exp}
    if claims:
        payload.update(claims)

    return _pyjwt.encode(payload, secret, algorithm=algorithm)


def validate(
    token: str,
    secret: str = DEFAULT_SECRET,
    algorithms: tuple[str, ...] = (DEFAULT_ALGORITHM,),
) -> TokenData:
    try:
        payload = _pyjwt.decode(token, secret, algorithms=algorithms)
    except _pyjwt.ExpiredSignatureError as e:
        raise TokenIsExpiredError("The token has expired") from e
    except _pyjwt.InvalidTokenError as e:
        raise TokenIsInvalidError(f"The token is invalid: {e}") from e

    try:
        sub = payload.pop("sub")
        iat = datetime.fromtimestamp(payload.pop("iat"), tz=timezone.utc)
        exp = datetime.fromtimestamp(payload.pop("exp"), tz=timezone.utc)
    except KeyError as e:
        raise TokenIsInvalidError(f"The token is missing required claim: {e}") from e

    return TokenData(sub=sub, iat=iat, exp=exp, claims=payload)
