"""TLS helpers for optional web fetches.

Verification is never disabled. ``SCS_FKB_CA_BUNDLE`` names an explicit bundle;
without it the interpreter default is used, with one fallback attempt against the
system bundle when the default trust store rejects a certificate (common in
virtual environments on macOS). The fallback is recorded by the caller through
the error it would otherwise raise.
"""

from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.request
from typing import Any

CA_ENV = "SCS_FKB_CA_BUNDLE"
SYSTEM_BUNDLES = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt")


def tls_context(cafile: str | None = None) -> ssl.SSLContext:
    bundle = (cafile or os.environ.get(CA_ENV, "")).strip()
    if bundle:
        return ssl.create_default_context(cafile=bundle)
    return ssl.create_default_context()


def _is_cert_error(exc: BaseException) -> bool:
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    return isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError)


def open_url(request: urllib.request.Request, timeout: float, *, context: Any = None) -> Any:
    """Open ``request`` with certificate verification, with one system-bundle retry."""
    chosen = context or tls_context()
    try:
        return urllib.request.urlopen(request, timeout=timeout, context=chosen)
    except (ssl.SSLCertVerificationError, urllib.error.URLError) as exc:
        if not _is_cert_error(exc):
            raise
        if os.environ.get(CA_ENV, "").strip():
            raise
        for bundle in SYSTEM_BUNDLES:
            if not os.path.isfile(bundle):
                continue
            try:
                return urllib.request.urlopen(
                    request, timeout=timeout, context=ssl.create_default_context(cafile=bundle)
                )
            except (ssl.SSLCertVerificationError, urllib.error.URLError) as retry:
                if not _is_cert_error(retry):
                    raise
                continue
        raise


__all__ = ["CA_ENV", "SYSTEM_BUNDLES", "open_url", "tls_context"]
