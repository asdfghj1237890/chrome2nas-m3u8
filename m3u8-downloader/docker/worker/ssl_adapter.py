"""
HTTP Session factory with browser impersonation
Uses curl_cffi to mimic Chrome's TLS fingerprint (JA3)
This bypasses TLS fingerprinting-based anti-bot detection
"""

import logging
import ssl
import os

logger = logging.getLogger(__name__)

# Try to import curl_cffi for browser impersonation
try:
    from curl_cffi.requests import Session as CurlSession
    CURL_CFFI_AVAILABLE = True
    logger.info("curl_cffi available - browser TLS impersonation enabled")
except ImportError:
    CURL_CFFI_AVAILABLE = False
    logger.warning("curl_cffi not available - falling back to requests (may be blocked by TLS fingerprinting)")

# Fallback imports
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


# Cipher suite that includes legacy options for compatibility
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


class BrowserSession:
    """
    Wrapper around curl_cffi Session that mimics requests.Session interface.
    Uses Chrome TLS fingerprint to bypass anti-bot detection.
    """
    
    def __init__(self, impersonate: str = "chrome"):
        """
        Initialize a browser-like session.
        
        Args:
            impersonate: Browser to impersonate. Options:
                - "chrome" (latest Chrome)
                - "chrome110", "chrome116", "chrome120", etc.
                - "safari", "safari_ios"
                - "edge"
        """
        self.impersonate = impersonate
        self._session = CurlSession(impersonate=impersonate)
        self.cookies = self._session.cookies
        logger.debug(f"Created BrowserSession with impersonate={impersonate}")
    
    def _prepare_kwargs(self, kwargs):
        """Prepare request kwargs with defaults"""
        # Disable SSL verification by default
        if 'verify' not in kwargs:
            kwargs['verify'] = False
        # Force HTTP/1.1 to avoid issues with servers that send invalid HTTP/2 headers
        # Some CDNs return 'keep-alive' header which is invalid in HTTP/2
        from curl_cffi.const import CurlHttpVersion
        if 'http_version' not in kwargs:
            kwargs['http_version'] = CurlHttpVersion.V1_1
        return kwargs
    
    def get(self, url, **kwargs):
        """Send GET request"""
        kwargs = self._prepare_kwargs(kwargs)
        return self._session.get(url, **kwargs)
    
    def post(self, url, **kwargs):
        """Send POST request"""
        kwargs = self._prepare_kwargs(kwargs)
        return self._session.post(url, **kwargs)
    
    def head(self, url, **kwargs):
        """Send HEAD request"""
        kwargs = self._prepare_kwargs(kwargs)
        return self._session.head(url, **kwargs)
    
    def request(self, method, url, **kwargs):
        """Send request with given method"""
        kwargs = self._prepare_kwargs(kwargs)
        return self._session.request(method, url, **kwargs)
    
    def close(self):
        """Close the session"""
        self._session.close()


def create_legacy_session():
    """
    Create a standard HTTP Session with legacy SSL support.
    This uses requests library which is more compatible with various servers.
    
    Use this for m3u8 parsing and general requests.
    For segment downloads that need anti-bot bypass, use create_browser_session().
    
    Returns:
        requests.Session with legacy SSL support
    """
    session = requests.Session()
    adapter = LegacySSLAdapter()
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def create_impersonated_session():
    """
    Create an HTTP Session with browser TLS fingerprint impersonation.
    
    Uses curl_cffi with Chrome impersonation to bypass TLS fingerprinting.
    Falls back to requests if curl_cffi is not available.
    
    Use this specifically for segment downloads that are blocked by anti-bot detection.
    
    Returns:
        Session object (BrowserSession or requests.Session)
    """
    if CURL_CFFI_AVAILABLE:
        logger.info("Creating impersonated session with curl_cffi (Chrome TLS fingerprint)")
        return BrowserSession(impersonate="chrome")
    else:
        logger.warning("curl_cffi not available, falling back to requests (may be blocked by TLS fingerprinting)")
        return create_legacy_session()


def create_browser_session(impersonate: str = "chrome"):
    """
    Create a session that impersonates a specific browser.
    
    Args:
        impersonate: Browser to impersonate (chrome, safari, edge)
    
    Returns:
        BrowserSession if curl_cffi available, else requests.Session
    """
    if CURL_CFFI_AVAILABLE:
        return BrowserSession(impersonate=impersonate)
    else:
        logger.warning(f"Cannot impersonate {impersonate} - curl_cffi not available")
        return create_legacy_session()
