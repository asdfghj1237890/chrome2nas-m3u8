"""
M3U8 Parser
Parse m3u8 playlists and extract segment information
"""

import logging
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import m3u8
import urllib3
from ssl_adapter import create_legacy_session

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Check if brotli is available for requests
try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    logger.warning("brotli package not installed - removing 'br' from Accept-Encoding headers")


class M3U8Parser:
    """Parse m3u8 playlists and extract segment URLs"""
    
    def __init__(self, url: str, headers: Optional[Dict] = None):
        self.url = url
        self.headers = self._sanitize_headers(headers or {})
        self.base_url = self._get_base_url(url)
        self.session = create_legacy_session()
    
    def _sanitize_headers(self, headers: Dict) -> Dict:
        """
        Sanitize request headers to prevent decompression issues.
        Removes 'br' (brotli) from Accept-Encoding if brotli is not available.
        """
        if BROTLI_AVAILABLE:
            return headers
        
        sanitized = headers.copy()
        accept_encoding = sanitized.get('Accept-Encoding', '')
        
        if 'br' in accept_encoding:
            # Remove 'br' from Accept-Encoding
            parts = [p.strip() for p in accept_encoding.split(',')]
            parts = [p for p in parts if p.lower() != 'br']
            if parts:
                sanitized['Accept-Encoding'] = ', '.join(parts)
            else:
                sanitized.pop('Accept-Encoding', None)
            logger.info(f"Sanitized Accept-Encoding: {accept_encoding} -> {sanitized.get('Accept-Encoding', '(removed)')}")
        
        return sanitized
        
    def _get_base_url(self, url: str) -> str:
        """Extract base URL from m3u8 URL"""
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        path_parts = parsed.path.rsplit('/', 1)
        if len(path_parts) > 1:
            base += path_parts[0] + '/'
        return base
    
    def fetch_playlist(self) -> str:
        """Fetch m3u8 playlist content"""
        try:
            logger.info(f"Fetching playlist: {self.url}")
            response = self.session.get(
                self.url, 
                headers=self.headers,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch playlist: {e}")
            raise
    
    def parse(self) -> Dict:
        """
        Parse m3u8 playlist and return segment information
        
        Returns:
            Dict with keys:
                - segments: List of segment URLs
                - duration: Total duration in seconds
                - is_variant: Whether this is a master playlist
                - resolution: Video resolution if available
        """
        try:
            # Fetch playlist content
            content = self.fetch_playlist()
            
            # Log first 500 chars of content to diagnose parsing issues
            content_preview = content[:500] if len(content) > 500 else content
            logger.info(f"Playlist content preview ({len(content)} bytes):\n{content_preview}")
            
            # Parse with m3u8 library
            playlist = m3u8.loads(content, uri=self.url)
            
            # Check if this is a master playlist (with variants)
            if playlist.is_variant:
                logger.info("Master playlist detected, selecting best quality")
                return self._parse_master_playlist(playlist, content)
            else:
                logger.info("Media playlist detected")
                # Debug: log segment count before parsing
                logger.debug(f"Raw playlist has {len(playlist.segments)} segments, {len(playlist.playlists)} playlists")
                return self._parse_media_playlist(playlist, content)
        
        except Exception as e:
            logger.error(f"Failed to parse m3u8: {e}")
            raise
    
    def _parse_master_playlist(self, playlist: m3u8.M3U8, content: str = None) -> Dict:
        """Parse master playlist and select best quality variant"""
        if not playlist.playlists:
            raise ValueError("No variants found in master playlist")
        
        # Sort by bandwidth (quality) and select highest
        variants = sorted(
            playlist.playlists, 
            key=lambda p: p.stream_info.bandwidth,
            reverse=True
        )
        
        best_variant = variants[0]
        logger.info(f"Selected variant: {best_variant.stream_info.bandwidth} bps")
        
        # Get resolution if available
        resolution = None
        if best_variant.stream_info.resolution:
            width, height = best_variant.stream_info.resolution
            resolution = f"{width}x{height}"
        
        # Get absolute URL for variant playlist
        variant_url = urljoin(self.url, best_variant.uri)
        
        # Parse the selected variant (media playlist)
        variant_parser = M3U8Parser(variant_url, self.headers)
        variant_content = variant_parser.fetch_playlist()
        variant_playlist = m3u8.loads(variant_content, uri=variant_url)
        
        result = self._parse_media_playlist(variant_playlist, variant_content)
        result['resolution'] = resolution
        result['selected_variant_url'] = variant_url
        
        return result
    
    def _parse_media_playlist(self, playlist: m3u8.M3U8, content: str = None) -> Dict:
        """Parse media playlist and extract segment URLs"""
        segments = []
        total_duration = 0.0
        
        for segment in playlist.segments:
            # Get absolute URL for segment
            segment_url = urljoin(playlist.base_uri or self.url, segment.uri)
            
            segments.append({
                'url': segment_url,
                'duration': segment.duration,
                'index': len(segments)
            })
            
            total_duration += segment.duration
        
        if not segments:
            # Log the actual content for debugging
            if content:
                content_preview = content[:1000] if len(content) > 1000 else content
                logger.error(f"Playlist content (no segments found):\n{content_preview}")
            raise ValueError("No segments found in playlist")
        
        logger.info(f"Found {len(segments)} segments, total duration: {total_duration:.1f}s")
        
        # Check if encrypted and get encryption info
        encryption_info = self._get_encryption_info(playlist)
        has_encryption = encryption_info is not None
        
        if has_encryption:
            logger.info(f"Playlist is encrypted with {encryption_info['method']}")
        
        return {
            'segments': segments,
            'duration': int(total_duration),
            'segment_count': len(segments),
            'is_variant': False,
            'has_encryption': has_encryption,
            'encryption_key': encryption_info.get('key') if encryption_info else None,
            'encryption_iv': encryption_info.get('iv') if encryption_info else None,
            'base_url': playlist.base_uri or self.url
        }
    
    def _get_encryption_info(self, playlist: m3u8.M3U8) -> Optional[Dict]:
        """Get encryption key and IV if playlist is encrypted"""
        for segment in playlist.segments:
            if segment.key and segment.key.method == 'AES-128':
                try:
                    key_url = urljoin(playlist.base_uri or self.url, segment.key.uri)
                    logger.info(f"Fetching encryption key: {key_url}")
                    response = self.session.get(key_url, headers=self.headers, timeout=30)
                    response.raise_for_status()
                    key = response.content
                    
                    # Validate key length (AES-128 requires 16 bytes)
                    logger.info(f"Encryption key length: {len(key)} bytes")
                    if len(key) != 16:
                        logger.warning(f"Unexpected key length: {len(key)} bytes (expected 16)")
                        # Some servers return key with extra whitespace or headers
                        if len(key) > 16:
                            logger.info(f"Key preview (first 32 bytes): {key[:32]}")
                    
                    # Get IV from key info or use default
                    iv = None
                    if segment.key.iv:
                        # IV is usually specified as hex string like 0x...
                        iv_str = segment.key.iv
                        logger.info(f"IV from m3u8: {iv_str}")
                        if iv_str.startswith('0x') or iv_str.startswith('0X'):
                            iv = bytes.fromhex(iv_str[2:])
                        else:
                            iv = bytes.fromhex(iv_str)
                        logger.info(f"Parsed IV length: {len(iv)} bytes, value: {iv.hex()}")
                    else:
                        logger.info("No IV specified in m3u8, will use segment sequence number")
                    
                    return {
                        'method': 'AES-128',
                        'key': key,
                        'iv': iv
                    }
                except Exception as e:
                    logger.error(f"Failed to fetch encryption key: {e}")
                    return None
        return None
    
    def get_encryption_key(self, playlist: m3u8.M3U8) -> Optional[bytes]:
        """Get encryption key if playlist is encrypted (deprecated, use _get_encryption_info)"""
        info = self._get_encryption_info(playlist)
        return info.get('key') if info else None


def parse_m3u8(url: str, headers: Optional[Dict] = None) -> Dict:
    """
    Convenience function to parse m3u8 URL
    
    Args:
        url: M3U8 playlist URL
        headers: Optional HTTP headers
    
    Returns:
        Dict with segment information
    """
    parser = M3U8Parser(url, headers)
    return parser.parse()

