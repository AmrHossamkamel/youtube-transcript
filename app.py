import os
import logging
from flask import Flask, render_template, jsonify, request
from transcript_service import get_transcript_and_metadata
from urllib.parse import urlparse, parse_qs
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

def extract_video_id(url_or_id):
    """Extract video ID from YouTube URL or return the ID if already provided."""
    # If it's already a video ID (11 characters, alphanumeric with dashes/underscores)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Parse YouTube URL
    parsed_url = urlparse(url_or_id)
    
    # Handle different YouTube URL formats
    if 'youtube.com' in parsed_url.netloc:
        if '/watch' in parsed_url.path:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        elif '/embed/' in parsed_url.path:
            return parsed_url.path.split('/embed/')[-1].split('?')[0]
    elif 'youtu.be' in parsed_url.netloc:
        return parsed_url.path.lstrip('/')
    
    return None

@app.route('/')
def index():
    """Render the main page with API documentation and testing interface."""
    return render_template('index.html')

@app.route('/api/transcript/<video_id>', methods=['GET'])
def get_transcript_by_id(video_id):
    """Get transcript and metadata for a YouTube video by video ID."""
    try:
        # Get proxy from environment variable if set
        proxy_url = os.environ.get('METADATA_PROXY_URL')
        result = get_transcript_and_metadata(video_id, max_duration_minutes=20, proxy_url=proxy_url)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error processing video {video_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e),
            'video_id': video_id
        }), 400

@app.route('/api/transcript', methods=['POST'])
def get_transcript_by_url():
    """Get transcript and metadata for a YouTube video by URL."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'error': True,
                'message': 'Missing "url" field in request body'
            }), 400
        
        video_id = extract_video_id(data['url'])
        if not video_id:
            return jsonify({
                'error': True,
                'message': 'Invalid YouTube URL or video ID'
            }), 400
        
        # Get proxy from environment variable if set
        proxy_url = os.environ.get('METADATA_PROXY_URL')
        result = get_transcript_and_metadata(video_id, max_duration_minutes=20, proxy_url=proxy_url)
        return jsonify(result)
    
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e)
        }), 400

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': True,
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'error': True,
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
