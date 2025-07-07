let currentResults = null;

document.getElementById('transcriptForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const videoInput = document.getElementById('videoInput').value.trim();
    
    if (!videoInput) {
        showError('Please enter a YouTube URL or video ID');
        return;
    }
    
    showLoading(true);
    hideResults();
    hideError();
    
    try {
        let response;
        
        // Check if input looks like a video ID (11 characters, alphanumeric with dashes/underscores)
        if (/^[a-zA-Z0-9_-]{11}$/.test(videoInput)) {
            // Use GET endpoint for video ID
            const url = `/api/transcript/${videoInput}`;
            response = await fetch(url);
        } else {
            // Use POST endpoint for URL
            response = await fetch('/api/transcript', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: videoInput
                })
            });
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'An error occurred');
        }
        
        currentResults = data;
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'An error occurred while processing the request');
    } finally {
        showLoading(false);
    }
});

function showLoading(show) {
    const loading = document.getElementById('loading');
    loading.style.display = show ? 'block' : 'none';
}

function hideResults() {
    const results = document.getElementById('results');
    results.style.display = 'none';
}

function showError(message) {
    hideResults();
    
    const textResults = document.getElementById('textResults');
    textResults.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <i class="bi bi-exclamation-triangle me-2"></i>
            <strong>Error:</strong> ${escapeHtml(message)}
        </div>
    `;
    
    document.getElementById('results').style.display = 'block';
}

function hideError() {
    // Error messages are shown in the same results area, so this is handled by hideResults()
}

function displayResults(data) {
    const textResults = document.getElementById('textResults');
    const jsonResults = document.getElementById('jsonResults');
    
    // Create metadata section
    const metadata = data.video_metadata || {};
    const metadataHtml = `
        <div class="row mb-4">
            <div class="col-md-6">
                <h6><i class="bi bi-info-circle me-2"></i>Video Information</h6>
                <table class="table table-sm">
                    <tr><td><strong>Video ID:</strong></td><td><code>${escapeHtml(data.video_id)}</code></td></tr>
                    <tr><td><strong>Title:</strong></td><td>${escapeHtml(metadata.title || 'N/A')}</td></tr>
                    <tr><td><strong>Channel:</strong></td><td>${escapeHtml(metadata.channel_name || 'N/A')}</td></tr>
                    <tr><td><strong>Duration:</strong></td><td>${escapeHtml(metadata.duration || 'N/A')}</td></tr>
                    <tr><td><strong>Views:</strong></td><td>${metadata.view_count ? formatNumber(metadata.view_count) : 'N/A'}</td></tr>
                    <tr><td><strong>Upload Date:</strong></td><td>${escapeHtml(metadata.upload_date || 'N/A')}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6><i class="bi bi-translate me-2"></i>Transcript Information</h6>
                <table class="table table-sm">
                    <tr><td><strong>Language:</strong></td><td><code>${escapeHtml(data.language_code)}</code></td></tr>
                    <tr><td><strong>Type:</strong></td><td><span class="badge ${data.language_type === 'en' ? 'bg-success' : 'bg-info'}">${data.language_type === 'en' ? 'English' : 'Non-English'}</span></td></tr>
                    <tr><td><strong>Segments:</strong></td><td>${data.total_segments || data.captions?.length || 0}</td></tr>
                    <tr><td><strong>Duration Extracted:</strong></td><td>20 minutes</td></tr>
                </table>
            </div>
        </div>
    `;
    
    // Create description section if available
    const descriptionHtml = metadata.description ? `
        <div class="mb-4">
            <h6><i class="bi bi-file-text me-2"></i>Description</h6>
            <div class="p-3 bg-dark rounded">
                <p class="mb-0 small">${escapeHtml(metadata.description).replace(/\n/g, '<br>')}</p>
            </div>
        </div>
    ` : '';
    
    // Create full text section for text tab
    const fullTextHtml = `
        <div class="mb-4">
            <h6><i class="bi bi-chat-quote me-2"></i>Full Transcript Text</h6>
            <div class="p-3 bg-dark rounded" style="max-height: 500px; overflow-y: auto;">
                <pre class="mb-0 small text-white">${escapeHtml(data.full_text || 'No transcript text available')}</pre>
            </div>
        </div>
    `;
    
    // Fill text tab
    textResults.innerHTML = metadataHtml + descriptionHtml + fullTextHtml;
    
    // Fill JSON tab
    jsonResults.innerHTML = `
        <div class="mb-4">
            <h6><i class="bi bi-code me-2"></i>Complete JSON Response</h6>
            <pre class="bg-dark p-3 rounded small" style="max-height: 600px; overflow-y: auto;"><code id="jsonOutput">${JSON.stringify(data, null, 2)}</code></pre>
        </div>
    `;
    
    document.getElementById('results').style.display = 'block';
}

function copyCurrentTab() {
    if (!currentResults) return;
    
    // Check which tab is active
    const textTab = document.getElementById('text-tab');
    const jsonTab = document.getElementById('json-tab');
    
    let textToCopy = '';
    
    if (textTab.classList.contains('active')) {
        // Copy full text content
        textToCopy = currentResults.full_text || 'No transcript text available';
    } else if (jsonTab.classList.contains('active')) {
        // Copy JSON content
        textToCopy = JSON.stringify(currentResults, null, 2);
    }
    
    if (textToCopy) {
        navigator.clipboard.writeText(textToCopy).then(() => {
            // Show temporary success message
            const button = event.target.closest('button');
            const originalHtml = button.innerHTML;
            button.innerHTML = '<i class="bi bi-check me-1"></i>Copied!';
            button.classList.add('btn-success');
            button.classList.remove('btn-outline-secondary');
            
            setTimeout(() => {
                button.innerHTML = originalHtml;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-secondary');
            }, 2000);
        }).catch(() => {
            alert('Failed to copy to clipboard');
        });
    }
}

function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}
