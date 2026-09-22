#!/usr/bin/env python3
"""
CVE Results Web Server
Display DPDT-Resolver results
"""

import os
import json
import socket
from pathlib import Path
from flask import Flask, render_template, jsonify, send_from_directory, send_file, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import time
import signal
import re

app = Flask(__name__)
CORS(app)

# Configure results directory path
RESULTS_DIR = Path('/home/jian1000/data3/LLMMockSystem/dynamic_trace/results')


def get_target_port(port=8000):
    return port


def get_cve_list():
    """Get all CVE directory list"""
    if not RESULTS_DIR.exists():
        return []

    cves = []
    for item in sorted(RESULTS_DIR.iterdir()):
        if item.is_dir() and item.name.startswith('CVE-'):
            cves.append(item.name)
    return cves


def get_cve_files(cve_id):
    """Get all files for specified CVE"""
    cve_dir = RESULTS_DIR / cve_id
    if not cve_dir.exists():
        return []

    files = []
    for file_path in sorted(cve_dir.rglob('*')):
        if file_path.is_file():
            rel_path = file_path.relative_to(cve_dir)
            files.append({
                'name': file_path.name,
                'path': str(rel_path),
                'size': file_path.stat().st_size,
                'type': file_path.suffix
            })
    return files


def load_json_file(file_path):
    """Load JSON file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {'error': str(e)}


@app.route('/')
def index():
    """Home page - Display all CVE list"""
    cves = get_cve_list()
    return render_template('index.html', cves=cves, total=len(cves))


@app.route('/api/cves')
def api_cves():
    """API: 获取所有CVE列表"""
    cves = get_cve_list()
    return jsonify({'cves': cves, 'total': len(cves)})


@app.route('/cve/<cve_id>')
def cve_detail(cve_id):
    """CVE detail page"""
    files = get_cve_files(cve_id)
    return render_template('cve_detail.html', cve_id=cve_id, files=files)


@app.route('/api/cve/<cve_id>')
def api_cve_detail(cve_id):
    """API: Get CVE detailed information"""
    files = get_cve_files(cve_id)
    cve_dir = RESULTS_DIR / cve_id

    # Load all JSON file content
    data = {}
    for file_info in files:
        if file_info['type'] == '.json':
            file_path = cve_dir / file_info['path']
            file_key = file_info['name'].replace(f"{cve_id}-", "").replace(".json", "")
            data[file_key] = load_json_file(file_path)

    return jsonify({
        'cve_id': cve_id,
        'files': files,
        'data': data
    })


@app.route('/api/cve/<cve_id>/file/<path:filename>')
def api_cve_file(cve_id, filename):
    """API: Get specified file content"""
    file_path = RESULTS_DIR / cve_id / filename

    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404

    if file_path.suffix == '.json':
        return jsonify(load_json_file(file_path))
    elif file_path.suffix == '.html':
        return send_file(file_path)
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'content': content})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/download/<cve_id>/<path:filename>')
def download_file(cve_id, filename):
    """Download file"""
    directory = RESULTS_DIR / cve_id
    return send_from_directory(directory, filename, as_attachment=True)


@app.route('/api/cve/<cve_id>/run_analysis', methods=['POST'])
def run_cve_analysis(cve_id):
    """API: Trigger the recursive analysis pipeline for a specific CVE"""
    
    # Basic security validation to prevent command injection
    if not re.match(r'^CVE-\d{4}-\d+$', cve_id, re.IGNORECASE):
        return jsonify({'error': 'Invalid CVE format'}), 400

    # Construct the shell command string
    # Included `mkdir -p` to ensure the target directory exists before moving files
    cmd = (
        f"cd /home/jian1000/data3/LLMMockSystem/dynamic_trace && "
        f"python3 run_recursive_api_analysis.py ../cve/benchmark/{cve_id}/run_exploit.sh "
        f"--vulnerable-file ../cve/benchmark/{cve_id}/vulnerable_versions.json "
        f"--CVE {cve_id} "
        f"--requirements ../cve/benchmark/{cve_id}/requirements.txt && "
        f"mkdir -p /home/jian1000/data3/LLMMockSystem/dynamic_trace/results/{cve_id} && "
        f"mv {cve_id}* /home/jian1000/data3/LLMMockSystem/dynamic_trace/results/{cve_id}/"
    )

    try:
        # shell=True is required because we are using '&&' and the wildcard '*'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Execution successful
            return jsonify({'status': 'success', 'output': result.stdout})
        else:
            # If the script fails, return the standard error (or standard output if stderr is empty)
            return jsonify({'error': result.stderr or result.stdout}), 500
            
    except Exception as e:
        # Catch unexpected server-side exceptions
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = get_target_port()
    print(f"\n{'='*60}")
    print(f"🚀 CVE Results Web Server Starting...")
    print(f"{'='*60}")
    print(f"📁 Results Directory: {RESULTS_DIR}")
    print(f"🌐 Server URL: http://localhost:{port}")
    print(f"{'='*60}\n")

    app.run(host='0.0.0.0', port=port, debug=True)
