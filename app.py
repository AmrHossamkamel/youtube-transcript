import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from transcript_service import TranscriptService
from proxy_manager import ProxyManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize services
proxy_manager = ProxyManager()
transcript_service = TranscriptService(proxy_manager)

@app.route('/')
def index():
    """Main page with transcript extraction form"""
    proxy_stats = proxy_manager.get_proxy_stats()
    return render_template('index.html', proxy_stats=proxy_stats)

@app.route('/extract', methods=['POST'])
def extract_transcript():
    """Extract transcript from YouTube video"""
    try:
        video_url = request.form.get('video_url', '').strip()
        if not video_url:
            flash('Please provide a YouTube video URL', 'error')
            return redirect(url_for('index'))
        
        # Extract video ID from URL
        video_id = transcript_service.extract_video_id(video_url)
        if not video_id:
            flash('Invalid YouTube URL. Please provide a valid YouTube video URL.', 'error')
            return redirect(url_for('index'))
        
        # Get transcript
        transcript_data = transcript_service.get_transcript(video_id)
        if transcript_data['success']:
            flash(f'Transcript extracted successfully using proxy: {transcript_data["proxy_used"]}', 'success')
            return render_template('index.html', 
                                 transcript=transcript_data['transcript'],
                                 video_id=video_id,
                                 proxy_used=transcript_data['proxy_used'],
                                 proxy_stats=proxy_manager.get_proxy_stats())
        else:
            flash(f'Failed to extract transcript: {transcript_data["error"]}', 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        logger.error(f"Error in extract_transcript: {str(e)}")
        flash('An unexpected error occurred while extracting the transcript', 'error')
        return redirect(url_for('index'))

@app.route('/api/transcript/<video_id>')
def api_get_transcript(video_id):
    """API endpoint to get transcript for a video ID"""
    try:
        transcript_data = transcript_service.get_transcript(video_id)
        return jsonify(transcript_data)
    except Exception as e:
        logger.error(f"Error in API transcript request: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'transcript': None,
            'proxy_used': None
        }), 500

@app.route('/api/proxy-stats')
def api_proxy_stats():
    """API endpoint to get proxy statistics"""
    try:
        stats = proxy_manager.get_proxy_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting proxy stats: {str(e)}")
        return jsonify({'error': 'Failed to get proxy statistics'}), 500

@app.route('/reset-proxy-stats', methods=['POST'])
def reset_proxy_stats():
    """Reset proxy statistics"""
    try:
        proxy_manager.reset_stats()
        flash('Proxy statistics have been reset', 'success')
    except Exception as e:
        logger.error(f"Error resetting proxy stats: {str(e)}")
        flash('Failed to reset proxy statistics', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
