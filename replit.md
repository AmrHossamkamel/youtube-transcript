# YouTube Transcript API

## Overview

This is a Flask-based web application that provides an API for extracting transcripts and metadata from YouTube videos. The application offers both a web interface for testing and REST API endpoints for programmatic access. It handles various YouTube URL formats, extracts video metadata through web scraping, and provides clean, processed transcripts with language detection.

## System Architecture

The application follows a simple three-tier architecture:

1. **Presentation Layer**: HTML frontend with Bootstrap UI and JavaScript for API interaction
2. **Application Layer**: Flask web framework handling HTTP requests and business logic
3. **Service Layer**: Dedicated transcript service for YouTube API integration and data processing

The architecture prioritizes simplicity and maintainability, using a monolithic design suitable for a focused API service.

## Key Components

### Core Application Files
- **app.py**: Main Flask application with route handlers and URL parsing logic
- **main.py**: Application entry point for development server
- **transcript_service.py**: Core business logic for transcript extraction and metadata scraping
- **templates/index.html**: Web interface with API documentation and testing form
- **static/app.js**: Frontend JavaScript for form handling and API interaction

### Service Architecture
- **URL Processing**: Flexible parsing supporting multiple YouTube URL formats (youtube.com, youtu.be, embed URLs)
- **Transcript Extraction**: Integration with YouTube Transcript API for caption retrieval
- **Metadata Scraping**: Web scraping approach for video information extraction
- **Text Processing**: Content cleaning to remove filler words and normalize formatting

## Data Flow

1. **Input Processing**: User provides YouTube URL or video ID through web interface or API
2. **Video ID Extraction**: URL parsing logic extracts standardized video ID
3. **Metadata Retrieval**: Concurrent web scraping for video title, duration, and channel information
4. **Transcript Fetching**: YouTube Transcript API call with language preference handling
5. **Content Processing**: Text cleaning and normalization of transcript content
6. **Response Formation**: JSON response with combined metadata and processed transcript

## External Dependencies

### Core Libraries
- **Flask**: Web framework for HTTP handling and templating
- **youtube-transcript-api**: Primary library for transcript extraction
- **requests**: HTTP client for metadata scraping with proxy support

### Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme
- **Bootstrap Icons**: Icon library for interface elements

### YouTube Integration
- Uses YouTube Transcript API for caption access
- Web scraping for metadata due to YouTube Data API limitations
- Handles multiple transcript languages with automatic fallback
- Proxy support for metadata extraction via METADATA_PROXY_URL environment variable

## Deployment Strategy

### Development Setup
- Flask development server on port 5000
- Debug mode enabled for development
- Environment-based secret key configuration

### Production Considerations
- Designed for containerized deployment (0.0.0.0 host binding)
- Environment variable support for configuration
- Logging configured for debugging and monitoring

### Scalability Approach
- Stateless design for horizontal scaling
- No database dependencies for simplified deployment
- External API rate limiting considerations built into service layer

## User Preferences

Preferred communication style: Simple, everyday language.

## Changelog

Changelog:
- July 02, 2025. Initial setup
- July 02, 2025. Added proxy support for metadata extraction via METADATA_PROXY_URL environment variable