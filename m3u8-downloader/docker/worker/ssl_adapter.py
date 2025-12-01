"""
Custom SSL Adapter with legacy cipher support
Handles servers that require specific/legacy TLS cipher suites
"""

import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


# Cipher suite that includes legacy options for compatibility
# This is a broad set that should work with most servers including legacy ones
LEGACY_CIPHERS = (
    'DEFAULT:!aNULL:!eNULL:!MD5:@SECLEVEL=1'
)


class LegacySSLAdapter(HTTPAdapter):
    """
    HTTPAdapter with custom SSL context that supports legacy ciphers.
    Useful for servers with non-standard TLS configurations.
    """
    
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers(LEGACY_CIPHERS)
        # Enable legacy renegotiation for older servers (Python 3.12+)
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


def create_legacy_session() -> requests.Session:
    """
    Create a requests Session with legacy SSL support.
    Use this for servers that fail with standard SSL handshake.
    """
    session = requests.Session()
    adapter = LegacySSLAdapter()
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

