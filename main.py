import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from claude_client import ClaudeClient
from github_utils import GitHubUtils
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

# Initialize clients
claude_client = ClaudeClient()
github_utils = GitHubUtils()

# Store current state
current_state = {
    'repo_url': '',
    'repo_name': '',
    'github_token': '',
    'errors': [],
    'fixes': []
}

def parse_error_log(log_content):
    """Parse error log and extract error information"""
    errors = []
    
    # Split by error entries
    error_entries = log_content.split('\n\n')
    
    for entry in error_entries:
        if 'ERROR' in entry:
            # Extract file name
            file_match = re.search(r'File: ([^,]+)', entry)
            file_path = file_match.group(1) if file_match else 'unknown'
            
            # Extract error message
            lines = entry.split('\n')
            error_msg = '\n'.join(lines)
            
            errors.append({
                'file': file_path,
                'log': error_msg
            })
    
    return errors

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', state=current_state)

@app.route('/connect_repo', methods=['POST'])
def connect_repo():
    """Connect to a GitHub repository"""
    repo_url = request.form.get('repo_url', '').strip()
    github_token = request.form.get('github_token', '').strip()
    
    if not repo_url:
        return jsonify({'error': 'Repository URL is required'}), 400
    
    # Extract repo name from URL
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    
    try:
        # Clone or pull repository
        local_path, repo = github_utils.clone_or_pull_repo(repo_url, repo_name, github_token)
        
        current_state['repo_url'] = repo_url
        current_state['repo_name'] = repo_name
        current_state['github_token'] = github_token
        current_state['repo_path'] = local_path
        
        return jsonify({
            'success': True,
            'message': f'Connected to {repo_name}',
            'repo_name': repo_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/scan_errors', methods=['POST'])
def scan_errors():
    """Scan for errors in the log file"""
    if not current_state.get('repo_path'):
        return jsonify({'error': 'No repository connected'}), 400
    
    # Read error log
    log_path = 'logs/error.log'
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            log_content = f.read()
    else:
        return jsonify({'error': 'No error log found'}), 404
    
    # Parse errors
    errors = parse_error_log(log_content)
    current_state['errors'] = errors
    
    return jsonify({
        'success': True,
        'errors': errors,
        'count': len(errors)
    })

@app.route('/analyze_error', methods=['POST'])
def analyze_error():
    """Analyze an error using Claude AI"""
    data = request.json
    error_log = data.get('error_log', '')
    file_path = data.get('file_path', '')
    
    if not current_state.get('repo_path'):
        return jsonify({'error': 'No repository connected'}), 400
    
    # Get file content from repo
    related_code = github_utils.get_file_content(current_state['repo_path'], file_path)
    
    if not related_code:
        related_code = "# File not found in repository"
    
    # Analyze with Claude
    result = claude_client.analyze_error(error_log, related_code, file_path)
    
    # Store the fix suggestion
    fix_data = {
        'file_path': file_path,
        'error_log': error_log,
        'original_code': related_code,
        **result
    }
    current_state['fixes'].append(fix_data)
    
    return jsonify(result)

@app.route('/apply_fix', methods=['POST'])
def apply_fix():
    """Apply the suggested fix to the repository"""
    data = request.json
    file_path = data.get('file_path', '')
    fixed_code = data.get('fixed_code', '')
    
    if not current_state.get('repo_path'):
        return jsonify({'error': 'No repository connected'}), 400
    
    # Apply fix and push
    result = github_utils.apply_fix_and_push(
        current_state['repo_path'],
        file_path,
        fixed_code,
        current_state.get('github_token')
    )
    
    return jsonify(result)

@app.route('/webhook', methods=['POST'])
def webhook():
    """GitHub webhook endpoint"""
    if request.method == 'POST':
        payload = request.json
        
        # Handle push events
        if 'ref' in payload and 'repository' in payload:
            repo_url = payload['repository']['clone_url']
            repo_name = payload['repository']['name']
            
            try:
                # Pull latest changes
                local_path, repo = github_utils.clone_or_pull_repo(repo_url, repo_name)
                
                return jsonify({
                    'success': True,
                    'message': f'Webhook received for {repo_name}'
                }), 200
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        return jsonify({'message': 'Webhook received'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
