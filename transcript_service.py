import logging
import re
from typing import Dict, Optional, List
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import requests
from proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

class TranscriptService:
    def __init__(self, proxy_manager: ProxyManager):
        """Initialize transcript service with proxy manager"""
        self.proxy_manager = proxy_manager
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        # Common YouTube URL patterns
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                logger.debug(f"Extracted video ID: {video_id}")
                return video_id
        
        logger.warning(f"Could not extract video ID from URL: {url}")
        return None
    
    def get_transcript_with_proxy(self, video_id: str, proxy_url: str) -> Dict:
        """Get transcript using a specific proxy"""
        try:
            # Set proxy for the youtube-transcript-api
            proxies = self.proxy_manager.format_proxy_dict(proxy_url)
            
            # Monkey patch the requests session to use proxy
            import requests
            original_get = requests.get
            original_post = requests.post
            
            def proxied_get(*args, **kwargs):
                kwargs['proxies'] = proxies
                kwargs['timeout'] = kwargs.get('timeout', 15)
                return original_get(*args, **kwargs)
            
            def proxied_post(*args, **kwargs):
                kwargs['proxies'] = proxies
                kwargs['timeout'] = kwargs.get('timeout', 15)
                return original_post(*args, **kwargs)
            
            requests.get = proxied_get
            requests.post = proxied_post
            
            try:
                # Try to get transcript in different languages (priority order)
                languages = ['en', 'en-US', 'en-GB', 'ar', 'auto']
                transcript = None
                
                for lang in languages:
                    try:
                        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                        
                        # Try to find manually created transcript first
                        try:
                            transcript = transcript_list.find_manually_created_transcript([lang])
                            logger.info(f"Found manually created transcript in {lang} using proxy {proxy_url}")
                            break
                        except NoTranscriptFound:
                            pass
                        
                        # Try generated transcript
                        try:
                            transcript = transcript_list.find_generated_transcript([lang])
                            logger.info(f"Found generated transcript in {lang} using proxy {proxy_url}")
                            break
                        except NoTranscriptFound:
                            continue
                            
                    except Exception as e:
                        logger.debug(f"Failed to get transcript in {lang} using proxy {proxy_url}: {str(e)}")
                        continue
                
                if not transcript:
                    # Try to get any available transcript
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    available_transcripts = list(transcript_list)
                    if available_transcripts:
                        transcript = available_transcripts[0]
                        logger.info(f"Using available transcript: {transcript.language} via proxy {proxy_url}")
                    else:
                        raise NoTranscriptFound("No transcripts available for this video")
                
                # Fetch the transcript
                transcript_data = transcript.fetch()
                
                # Format transcript text
                formatted_transcript = self.format_transcript(transcript_data)
                
                return {
                    'success': True,
                    'transcript': formatted_transcript,
                    'raw_transcript': transcript_data,
                    'language': transcript.language,
                    'is_generated': transcript.is_generated,
                    'error': None
                }
                
            finally:
                # Restore original requests functions
                requests.get = original_get
                requests.post = original_post
                
        except TranscriptsDisabled:
            error_msg = "Transcripts are disabled for this video"
            logger.warning(f"Transcripts disabled for video {video_id}")
            return {'success': False, 'transcript': None, 'error': error_msg}
            
        except NoTranscriptFound:
            error_msg = "No transcript found for this video"
            logger.warning(f"No transcript found for video {video_id}")
            return {'success': False, 'transcript': None, 'error': error_msg}
            
        except VideoUnavailable:
            error_msg = "Video is unavailable or private"
            logger.warning(f"Video unavailable: {video_id}")
            return {'success': False, 'transcript': None, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"Error fetching transcript: {str(e)}"
            logger.error(f"Error getting transcript for {video_id} with proxy {proxy_url}: {str(e)}")
            return {'success': False, 'transcript': None, 'error': error_msg}
    
    def get_transcript_without_proxy(self, video_id: str) -> Dict:
        """Get transcript without using proxy (direct connection)"""
        try:
            # Try to get transcript in different languages (priority order)
            languages = ['en', 'en-US', 'en-GB', 'ar']
            transcript = None
            
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            for lang in languages:
                try:
                    # Try to find manually created transcript first
                    try:
                        transcript = transcript_list.find_manually_created_transcript([lang])
                        logger.info(f"Found manually created transcript in {lang}")
                        break
                    except NoTranscriptFound:
                        pass
                    
                    # Try generated transcript
                    try:
                        transcript = transcript_list.find_generated_transcript([lang])
                        logger.info(f"Found generated transcript in {lang}")
                        break
                    except NoTranscriptFound:
                        continue
                        
                except Exception as e:
                    logger.debug(f"Failed to get transcript in {lang}: {str(e)}")
                    continue
            
            if not transcript:
                # Try to get any available transcript
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript = available_transcripts[0]
                    logger.info(f"Using available transcript: {transcript.language}")
                else:
                    raise NoTranscriptFound("No transcripts available for this video")
            
            # Fetch the transcript
            transcript_data = transcript.fetch()
            
            # Format transcript text
            formatted_transcript = self.format_transcript(transcript_data)
            
            return {
                'success': True,
                'transcript': formatted_transcript,
                'raw_transcript': transcript_data,
                'language': transcript.language,
                'is_generated': transcript.is_generated,
                'error': None
            }
            
        except TranscriptsDisabled:
            error_msg = "Transcripts are disabled for this video"
            logger.warning(f"Transcripts disabled for video {video_id}")
            return {'success': False, 'transcript': None, 'error': error_msg}
            
        except NoTranscriptFound:
            error_msg = "No transcript found for this video"
            logger.warning(f"No transcript found for video {video_id}")
            return {'success': False, 'transcript': None, 'error': error_msg}
            
        except VideoUnavailable:
            error_msg = "Video is unavailable or private"
            logger.warning(f"Video unavailable: {video_id}")
            return {'success': False, 'transcript': None, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"Error fetching transcript: {str(e)}"
            logger.error(f"Error getting transcript for {video_id}: {str(e)}")
            return {'success': False, 'transcript': None, 'error': error_msg}

    def get_transcript(self, video_id: str) -> Dict:
        """Get transcript using ONLY proxy rotation - no direct connections"""
        if not video_id:
            return {'success': False, 'transcript': None, 'error': 'Invalid video ID', 'proxy_used': None}
        
        logger.info(f"Starting transcript extraction for {video_id} using ONLY proxies")
        
        attempted_proxies = set()
        
        # Try ALL available proxies until we find one that works
        for attempt in range(len(self.proxy_manager.proxies)):
            proxy_url = self.proxy_manager.get_working_proxy()
            
            if not proxy_url:
                logger.error("No working proxies available - cannot proceed without proxy")
                return {
                    'success': False,
                    'transcript': None,
                    'error': 'No working proxies available. All proxies have failed.',
                    'proxy_used': None
                }
            
            if proxy_url in attempted_proxies:
                # Get a different proxy
                remaining_proxies = [p for p in self.proxy_manager.proxies if p not in attempted_proxies]
                if remaining_proxies:
                    proxy_url = self.proxy_manager.get_random_proxy()
                    while proxy_url in attempted_proxies and len(attempted_proxies) < len(self.proxy_manager.proxies):
                        proxy_url = self.proxy_manager.get_random_proxy()
                else:
                    logger.error("All proxies have been attempted and failed")
                    return {
                        'success': False,
                        'transcript': None,
                        'error': 'All available proxies have been tried and failed',
                        'proxy_used': None
                    }
            
            attempted_proxies.add(proxy_url)
            
            logger.info(f"Attempt {attempt + 1}/{len(self.proxy_manager.proxies)}: Using proxy {proxy_url}")
            
            result = self.get_transcript_with_proxy(video_id, proxy_url)
            
            if result['success']:
                # Update proxy stats for successful transcript fetch
                self.proxy_manager.update_proxy_stats(proxy_url, True, 1.0)
                result['proxy_used'] = proxy_url
                logger.info(f"SUCCESS: Got transcript for {video_id} using proxy {proxy_url}")
                return result
            else:
                # Update proxy stats for failed transcript fetch
                self.proxy_manager.update_proxy_stats(proxy_url, False, 0)
                logger.warning(f"FAILED: Proxy {proxy_url} failed: {result['error']}")
        
        # If all proxies failed
        logger.error(f"ALL PROXIES FAILED for video {video_id}")
        return {
            'success': False,
            'transcript': None,
            'error': f'All {len(self.proxy_manager.proxies)} proxies failed to extract transcript',
            'proxy_used': 'All proxies failed'
        }
    
    def format_transcript(self, transcript_data) -> str:
        """Format transcript data into readable text"""
        if not transcript_data:
            return ""
        
        formatted_lines = []
        
        # Handle both list format and FetchedTranscriptSnippet objects
        if hasattr(transcript_data, '__iter__'):
            for entry in transcript_data:
                # Handle FetchedTranscriptSnippet objects
                if hasattr(entry, 'text') and hasattr(entry, 'start'):
                    text = entry.text.strip()
                    start_time = entry.start
                # Handle dictionary format
                elif isinstance(entry, dict):
                    text = entry.get('text', '').strip()
                    start_time = entry.get('start', 0)
                else:
                    continue
                
                # Convert seconds to MM:SS format
                minutes = int(start_time // 60)
                seconds = int(start_time % 60)
                timestamp = f"[{minutes:02d}:{seconds:02d}]"
                
                if text:
                    formatted_lines.append(f"{timestamp} {text}")
        
        return "\n".join(formatted_lines)
    
    def get_video_info(self, video_id: str) -> Dict:
        """Get basic video information"""
        try:
            # This is a simple implementation - could be enhanced with actual video metadata
            return {
                'video_id': video_id,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'status': 'Available for transcript extraction'
            }
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return {
                'video_id': video_id,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'status': 'Unknown'
            }
