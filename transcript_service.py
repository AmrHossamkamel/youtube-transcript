import re
import requests
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import logging

def clean_transcript_text(text):
    """Clean transcript text by removing filler content and normalizing."""
    if not text:
        return ""
    
    # Remove common filler content
    filler_patterns = [
        r'\[Music\]',
        r'\[Applause\]',
        r'\[Laughter\]',
        r'\[Inaudible\]',
        r'\[Background music\]',
        r'\[♪.*?♪\]',
        r'\[.*?music.*?\]',
        r'\[.*?applause.*?\]',
        r'\[.*?laughter.*?\]',
    ]
    
    cleaned_text = text
    for pattern in filler_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
    
    # Clean up whitespace and normalize
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text

def extract_video_metadata(video_id, proxy_url=None):
    """Extract video metadata by scraping the YouTube page."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Configure proxy if provided
        proxies = None
        if proxy_url:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            logging.info(f"Using proxy for metadata extraction: {proxy_url}")
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        html_content = response.text
        
        metadata = {}
        
        # Extract title
        title_match = re.search(r'"title":"([^"]+)"', html_content)
        if title_match:
            metadata['title'] = title_match.group(1).replace('\\u0026', '&').replace('\\"', '"')
        else:
            # Fallback to meta tag
            title_match = re.search(r'<meta name="title" content="([^"]+)"', html_content)
            if title_match:
                metadata['title'] = title_match.group(1)
        
        # Extract description
        desc_match = re.search(r'"shortDescription":"([^"]+)"', html_content)
        if desc_match:
            metadata['description'] = desc_match.group(1).replace('\\n', '\n').replace('\\"', '"')
        
        # Extract channel name
        channel_match = re.search(r'"ownerChannelName":"([^"]+)"', html_content)
        if channel_match:
            metadata['channel_name'] = channel_match.group(1)
        else:
            # Fallback
            channel_match = re.search(r'"author":"([^"]+)"', html_content)
            if channel_match:
                metadata['channel_name'] = channel_match.group(1)
        
        # Extract duration (in seconds)
        duration_match = re.search(r'"lengthSeconds":"(\d+)"', html_content)
        if duration_match:
            metadata['duration_seconds'] = int(duration_match.group(1))
            # Convert to human readable format
            seconds = metadata['duration_seconds']
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            if hours > 0:
                metadata['duration'] = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                metadata['duration'] = f"{minutes}:{seconds:02d}"
        
        # Extract view count
        views_match = re.search(r'"viewCount":"(\d+)"', html_content)
        if views_match:
            metadata['view_count'] = int(views_match.group(1))
        
        # Extract upload date
        upload_match = re.search(r'"uploadDate":"([^"]+)"', html_content)
        if upload_match:
            metadata['upload_date'] = upload_match.group(1)
        else:
            # Try alternative pattern
            upload_match = re.search(r'"publishDate":"([^"]+)"', html_content)
            if upload_match:
                metadata['upload_date'] = upload_match.group(1)
        
        return metadata
        
    except Exception as e:
        logging.error(f"Error extracting metadata for video {video_id}: {str(e)}")
        return {}

def detect_language_type(language_code):
    """Determine if language is English or non-English."""
    english_codes = ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU', 'en-IN']
    return "en" if language_code in english_codes else "non-en"

def get_transcript_and_metadata(video_id, max_duration_minutes=20, proxy_url=None):
    """
    Extract transcript and metadata from a YouTube video.
    
    Args:
        video_id (str): YouTube video ID
        max_duration_minutes (int): Maximum duration to extract in minutes
        proxy_url (str, optional): Proxy URL for metadata extraction
    
    Returns:
        dict: Contains video_id, language_code, language_type, full_text, captions, and video_metadata
    """
    try:
        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get English transcript first
        transcript = None
        language_code = None
        
        try:
            # Try manual English transcript first
            for t in transcript_list:
                if t.language_code in ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU']:
                    if not t.is_generated:  # Prefer manual transcripts
                        transcript = t
                        language_code = t.language_code
                        break
            
            # If no manual English transcript, try auto-generated English
            if not transcript:
                for t in transcript_list:
                    if t.language_code in ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU']:
                        transcript = t
                        language_code = t.language_code
                        break
            
            # If no English transcript, get the first available transcript
            if not transcript:
                transcript = next(iter(transcript_list))
                language_code = transcript.language_code
                
        except StopIteration:
            raise Exception("No transcripts available for this video")
        
        # Fetch the transcript data
        transcript_data = transcript.fetch()
        
        # Filter by max duration (convert minutes to seconds)
        max_duration_seconds = max_duration_minutes * 60
        filtered_transcript = [
            entry for entry in transcript_data 
            if (entry['start'] if isinstance(entry, dict) else entry.start) <= max_duration_seconds
        ]
        
        # Clean and process transcript
        captions = []
        full_text_parts = []
        seen_texts = set()  # To remove duplicates
        
        for entry in filtered_transcript:
            # Handle both dict and object formats
            if isinstance(entry, dict):
                start_time = entry['start']
                duration = entry['duration'] 
                text = entry['text']
            else:
                start_time = entry.start
                duration = entry.duration
                text = entry.text
            
            cleaned_text = clean_transcript_text(text)
            
            if cleaned_text and cleaned_text not in seen_texts:
                seen_texts.add(cleaned_text)
                
                captions.append({
                    'start': start_time,
                    'duration': duration,
                    'text': cleaned_text
                })
                
                full_text_parts.append(cleaned_text)
        
        # Join all text parts
        full_text = ' '.join(full_text_parts)
        
        # Extract video metadata
        video_metadata = extract_video_metadata(video_id, proxy_url)
        
        # Determine language type
        language_type = detect_language_type(language_code)
        
        return {
            'video_id': video_id,
            'language_code': language_code,
            'language_type': language_type,
            'full_text': full_text,
            'captions': captions,
            'video_metadata': video_metadata,
            'total_segments': len(captions),
            'transcript_duration_minutes': max_duration_minutes,
            'actual_duration_extracted': max(entry['start'] if isinstance(entry, dict) else entry.start for entry in filtered_transcript) / 60 if filtered_transcript else 0
        }
        
    except VideoUnavailable:
        raise Exception(f"Video {video_id} is unavailable (private, deleted, or doesn't exist)")
    except TranscriptsDisabled:
        raise Exception(f"Transcripts are disabled for video {video_id}")
    except NoTranscriptFound:
        raise Exception(f"No transcripts found for video {video_id}")
    except Exception as e:
        logging.error(f"Error in get_transcript_and_metadata: {str(e)}")
        raise Exception(f"Failed to process video {video_id}: {str(e)}")
