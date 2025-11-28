"""
M3U8 Parser
Parse m3u8 playlists and extract segment information
"""

import logging
import requests
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import m3u8
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class M3U8Parser:
    """Parse m3u8 playlists and extract segment URLs"""
    
    def __init__(self, url: str, headers: Optional[Dict] = None):
        self.url = url
        self.headers = headers or {}
        self.base_url = self._get_base_url(url)
        
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
            response = requests.get(
                self.url, 
                headers=self.headers,
                timeout=30,
                allow_redirects=True,
                verify=False
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
            
            # Parse with m3u8 library
            playlist = m3u8.loads(content, uri=self.url)
            
            # Check if this is a master playlist (with variants)
            if playlist.is_variant:
                logger.info("Master playlist detected, selecting best quality")
                return self._parse_master_playlist(playlist)
            else:
                logger.info("Media playlist detected")
                return self._parse_media_playlist(playlist)
        
        except Exception as e:
            logger.error(f"Failed to parse m3u8: {e}")
            raise
    
    def _parse_master_playlist(self, playlist: m3u8.M3U8) -> Dict:
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
        
        result = self._parse_media_playlist(variant_playlist)
        result['resolution'] = resolution
        result['selected_variant_url'] = variant_url
        
        return result
    
    def _parse_media_playlist(self, playlist: m3u8.M3U8) -> Dict:
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
                    response = requests.get(key_url, headers=self.headers, verify=False, timeout=30)
                    response.raise_for_status()
                    key = response.content
                    
                    # Get IV from key info or use default
                    iv = None
                    if segment.key.iv:
                        # IV is usually specified as hex string like 0x...
                        iv_str = segment.key.iv
                        if iv_str.startswith('0x') or iv_str.startswith('0X'):
                            iv = bytes.fromhex(iv_str[2:])
                        else:
                            iv = bytes.fromhex(iv_str)
                    
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

