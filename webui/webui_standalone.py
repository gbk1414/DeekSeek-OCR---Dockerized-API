#!/usr/bin/env python3
"""
DeepSeek-OCR Standalone Web UI
로컬 PC에서 실행하여 원격 DeepSeek-OCR API 서버를 브라우저로 사용

Usage:
    python webui_standalone.py
    python webui_standalone.py --server http://your-server.com:8000
    python webui_standalone.py --port 8080
"""

import os
import sys
import argparse
import webbrowser
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import zipfile

# .env 파일 자동 로드 (있으면)
def load_env_file(env_file='.env'):
    """Load environment variables from .env file if it exists"""
    env_path = Path(env_file)
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # 환경 변수에 아직 없으면 설정
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()

# 현재 디렉토리와 상위 디렉토리에서 .env 파일 찾기
load_env_file('.env')  # 현재 디렉토리
load_env_file('../.env')  # 상위 디렉토리 (webui/ 폴더에서 실행 시)

# 기본 설정
DEFAULT_SERVER_URL = os.environ.get('DEEPSEEK_OCR_SERVER', 'http://localhost:8000')
DEFAULT_PORT = int(os.environ.get('DEEPSEEK_OCR_PORT', '8080'))

# FastAPI 앱 초기화
app = FastAPI(
    title="DeepSeek-OCR Web UI (Standalone)",
    description="Browser interface for DeepSeek-OCR API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
API_SERVER_URL = DEFAULT_SERVER_URL
TEMP_DIR = Path(tempfile.gettempdir()) / "deepseek_ocr_webui"
TEMP_DIR.mkdir(exist_ok=True)

# 작업 추적
processing_jobs = {}


def cleanup_old_files():
    """24시간 이상 된 임시 파일 삭제"""
    import time
    current_time = time.time()
    max_age = 24 * 3600

    if TEMP_DIR.exists():
        for item in TEMP_DIR.iterdir():
            if current_time - item.stat().st_mtime > max_age:
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception:
                    pass


async def process_files_batch(job_id: str, files: List[Path], custom_prompt: Optional[str] = None):
    """배치로 파일 처리하고 ZIP 생성"""
    try:
        processing_jobs[job_id]['status'] = 'processing'
        processing_jobs[job_id]['total'] = len(files)
        processing_jobs[job_id]['processed'] = 0

        # 결과 저장 디렉토리
        results_dir = TEMP_DIR / job_id
        results_dir.mkdir(exist_ok=True)

        # 각 파일 처리
        for idx, file_path in enumerate(files):
            try:
                processing_jobs[job_id]['current_file'] = file_path.name

                # 파일 타입 확인
                ext = file_path.suffix.lower()

                # API 엔드포인트 선택
                if ext == '.pdf':
                    endpoint = f"{API_SERVER_URL}/ocr/pdf"
                else:
                    endpoint = f"{API_SERVER_URL}/ocr/image"

                # API 요청
                with open(file_path, 'rb') as f:
                    files_data = {'file': (file_path.name, f, 'application/octet-stream')}
                    data = {}
                    if custom_prompt:
                        data['prompt'] = custom_prompt

                    response = requests.post(endpoint, files=files_data, data=data, timeout=300)

                if response.status_code == 200:
                    result = response.json()

                    # 결과 저장
                    output_file = results_dir / f"{file_path.stem}.md"

                    # PDF는 여러 페이지 결과를 합침
                    if 'results' in result:
                        content = ""
                        for page_result in result['results']:
                            if page_result.get('result'):
                                content += page_result['result'] + "\n\n<--- Page Split --->\n\n"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(content.strip())
                    # 이미지는 단일 결과
                    elif 'result' in result:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(result['result'])

                    processing_jobs[job_id]['successful'] += 1
                else:
                    raise Exception(f"API error: {response.status_code} - {response.text}")

                processing_jobs[job_id]['processed'] = idx + 1

            except Exception as e:
                processing_jobs[job_id]['failed'] += 1
                processing_jobs[job_id]['errors'].append(f"{file_path.name}: {str(e)}")

        # ZIP 파일 생성
        zip_path = TEMP_DIR / f"{job_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for md_file in results_dir.glob("*.md"):
                zipf.write(md_file, md_file.name)

        processing_jobs[job_id]['status'] = 'completed'
        processing_jobs[job_id]['zip_path'] = str(zip_path)
        processing_jobs[job_id]['completed_at'] = datetime.now().isoformat()

    except Exception as e:
        processing_jobs[job_id]['status'] = 'failed'
        processing_jobs[job_id]['error'] = str(e)


@app.on_event("startup")
async def startup_event():
    """시작 시 초기화"""
    cleanup_old_files()
    print(f"\n{'='*70}")
    print(f"  DeepSeek-OCR Web UI (Standalone)")
    print(f"{'='*70}")
    print(f"  Local URL:  http://localhost:{app.state.port}")
    print(f"  API Server: {API_SERVER_URL}")
    print(f"{'='*70}\n")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Web UI 페이지 제공"""
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeepSeek-OCR Web UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 0.95em; }
        .server-info {
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 0.85em;
        }
        .content { padding: 30px; }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            background: #f8f9ff;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .upload-area:hover { border-color: #764ba2; background: #f0f1ff; }
        .upload-area.dragover { border-color: #764ba2; background: #e8e9ff; transform: scale(1.02); }
        .upload-icon { font-size: 64px; margin-bottom: 20px; }
        input[type="file"] { display: none; }
        .file-list { margin-top: 20px; max-height: 300px; overflow-y: auto; }
        .file-item {
            background: #f8f9fa;
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .file-item .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .file-item .size { color: #6c757d; font-size: 0.9em; margin-left: 10px; }
        .file-item .remove {
            background: #dc3545;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }
        .file-item .remove:hover { background: #c82333; }
        .prompt-section { margin-top: 30px; }
        .prompt-section label { display: block; font-weight: 600; margin-bottom: 8px; color: #333; }
        .prompt-section textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
        }
        .prompt-section textarea:focus { outline: none; border-color: #667eea; }
        .buttons { margin-top: 30px; display: flex; gap: 12px; }
        button {
            flex: 1;
            padding: 14px 28px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-secondary:hover { background: #5a6268; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .progress-section { margin-top: 30px; display: none; }
        .progress-section.active { display: block; }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 16px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }
        .status-text { text-align: center; color: #666; margin-bottom: 16px; }
        .download-section {
            margin-top: 20px;
            padding: 20px;
            background: #d4edda;
            border-radius: 8px;
            border: 2px solid #c3e6cb;
            text-align: center;
        }
        .download-section h3 { color: #155724; margin-bottom: 12px; }
        .download-btn {
            background: #28a745;
            color: white;
            padding: 12px 32px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .download-btn:hover { background: #218838; }
        .error-section {
            margin-top: 20px;
            padding: 20px;
            background: #f8d7da;
            border-radius: 8px;
            border: 2px solid #f5c6cb;
        }
        .error-section h4 { color: #721c24; margin-bottom: 12px; }
        .error-list { color: #721c24; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 DeepSeek-OCR Web UI</h1>
            <p>PDF 및 이미지 파일을 업로드하여 OCR 처리 후 결과를 ZIP으로 다운로드하세요</p>
            <div class="server-info" id="serverInfo">
                ⚙️ API 서버 연결 확인 중...
            </div>
        </div>
        <div class="content">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <h3>파일을 드래그 앤 드롭하거나 클릭하여 업로드</h3>
                <p>PDF, JPG, PNG 등의 파일을 지원합니다</p>
                <input type="file" id="fileInput" multiple accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.webp">
            </div>
            <div class="file-list" id="fileList"></div>
            <div class="prompt-section">
                <label for="promptInput">OCR 프롬프트 (선택사항)</label>
                <textarea id="promptInput" rows="3" placeholder="기본값: <image>\\n<|grounding|>Convert the document to markdown."></textarea>
            </div>
            <div class="buttons">
                <button class="btn-primary" id="processBtn" onclick="processFiles()">OCR 처리 시작</button>
                <button class="btn-secondary" id="clearBtn" onclick="clearFiles()">초기화</button>
            </div>
            <div class="progress-section" id="progressSection">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%">0%</div>
                </div>
                <div class="status-text" id="statusText">대기 중...</div>
                <div id="downloadSection"></div>
                <div id="errorSection"></div>
            </div>
        </div>
    </div>
    <script>
        let selectedFiles = [];
        let jobId = null;
        let pollInterval = null;
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const processBtn = document.getElementById('processBtn');
        const progressSection = document.getElementById('progressSection');
        const progressFill = document.getElementById('progressFill');
        const statusText = document.getElementById('statusText');
        const downloadSection = document.getElementById('downloadSection');
        const errorSection = document.getElementById('errorSection');
        const serverInfo = document.getElementById('serverInfo');

        // 서버 연결 확인
        async function checkServerConnection() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                serverInfo.innerHTML = `✅ API 서버 연결됨: ${data.server_url}`;
                serverInfo.style.background = 'rgba(76, 175, 80, 0.3)';
            } catch (error) {
                serverInfo.innerHTML = `❌ API 서버 연결 실패`;
                serverInfo.style.background = 'rgba(244, 67, 54, 0.3)';
            }
        }
        checkServerConnection();

        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
        uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('dragover'); });
        uploadArea.addEventListener('drop', (e) => { e.preventDefault(); uploadArea.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
        fileInput.addEventListener('change', (e) => { handleFiles(e.target.files); });

        function handleFiles(files) {
            for (let file of files) {
                if (!selectedFiles.find(f => f.name === file.name)) {
                    selectedFiles.push(file);
                }
            }
            updateFileList();
        }

        function updateFileList() {
            fileList.innerHTML = '';
            selectedFiles.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <span class="name">${file.name}</span>
                    <span class="size">${formatFileSize(file.size)}</span>
                    <button class="remove" onclick="removeFile(${index})">삭제</button>
                `;
                fileList.appendChild(fileItem);
            });
            processBtn.disabled = selectedFiles.length === 0;
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
        }

        function clearFiles() {
            selectedFiles = [];
            updateFileList();
            fileInput.value = '';
            progressSection.classList.remove('active');
            downloadSection.innerHTML = '';
            errorSection.innerHTML = '';
        }

        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }

        async function processFiles() {
            if (selectedFiles.length === 0) {
                alert('파일을 선택해주세요');
                return;
            }
            const formData = new FormData();
            selectedFiles.forEach(file => { formData.append('files', file); });
            const customPrompt = document.getElementById('promptInput').value.trim();
            if (customPrompt) {
                formData.append('prompt', customPrompt);
            }
            processBtn.disabled = true;
            progressSection.classList.add('active');
            downloadSection.innerHTML = '';
            errorSection.innerHTML = '';
            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                if (result.job_id) {
                    jobId = result.job_id;
                    statusText.textContent = 'OCR 처리 중...';
                    startPolling();
                } else {
                    throw new Error('작업 ID를 받지 못했습니다');
                }
            } catch (error) {
                alert('오류 발생: ' + error.message);
                processBtn.disabled = false;
                progressSection.classList.remove('active');
            }
        }

        function startPolling() {
            pollInterval = setInterval(checkJobStatus, 1000);
        }

        async function checkJobStatus() {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                const status = await response.json();
                if (status.status === 'processing') {
                    const progress = Math.round((status.processed / status.total) * 100);
                    progressFill.style.width = progress + '%';
                    progressFill.textContent = progress + '%';
                    statusText.textContent = `처리 중... (${status.processed}/${status.total}) - ${status.current_file}`;
                } else if (status.status === 'completed') {
                    clearInterval(pollInterval);
                    progressFill.style.width = '100%';
                    progressFill.textContent = '100%';
                    statusText.textContent = '처리 완료!';
                    downloadSection.innerHTML = `
                        <div class="download-section">
                            <h3>✅ OCR 처리가 완료되었습니다!</h3>
                            <p>성공: ${status.successful} / 실패: ${status.failed}</p>
                            <a href="/api/download/${jobId}" class="download-btn" download>📥 결과 다운로드 (ZIP)</a>
                        </div>
                    `;
                    if (status.errors && status.errors.length > 0) {
                        errorSection.innerHTML = `
                            <div class="error-section">
                                <h4>⚠️ 일부 파일 처리 실패</h4>
                                <div class="error-list">
                                    ${status.errors.map(e => `<p>• ${e}</p>`).join('')}
                                </div>
                            </div>
                        `;
                    }
                    processBtn.disabled = false;
                } else if (status.status === 'failed') {
                    clearInterval(pollInterval);
                    statusText.textContent = '처리 실패';
                    errorSection.innerHTML = `
                        <div class="error-section">
                            <h4>❌ 처리 중 오류 발생</h4>
                            <p>${status.error}</p>
                        </div>
                    `;
                    processBtn.disabled = false;
                }
            } catch (error) {
                clearInterval(pollInterval);
                alert('상태 확인 중 오류 발생: ' + error.message);
                processBtn.disabled = false;
            }
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/api/health")
async def api_health():
    """API 서버 연결 확인"""
    try:
        response = requests.get(f"{API_SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            return {"status": "connected", "server_url": API_SERVER_URL, "server_health": response.json()}
        else:
            return {"status": "error", "server_url": API_SERVER_URL, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"status": "error", "server_url": API_SERVER_URL, "error": str(e)}


@app.post("/api/process")
async def api_process(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    prompt: Optional[str] = Form(None)
):
    """파일 처리 시작"""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # 작업 ID 생성
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # 임시 디렉토리에 파일 저장
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    file_paths = []
    for file in files:
        file_path = job_dir / file.filename
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        file_paths.append(file_path)

    # 작업 추적 초기화
    processing_jobs[job_id] = {
        'status': 'queued',
        'total': len(file_paths),
        'processed': 0,
        'successful': 0,
        'failed': 0,
        'current_file': '',
        'errors': [],
        'created_at': datetime.now().isoformat()
    }

    # 백그라운드에서 처리 시작
    background_tasks.add_task(process_files_batch, job_id, file_paths, prompt)

    return {"job_id": job_id, "total_files": len(file_paths)}


@app.get("/api/status/{job_id}")
async def api_status(job_id: str):
    """작업 상태 조회"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return processing_jobs[job_id]


@app.get("/api/download/{job_id}")
async def api_download(job_id: str):
    """결과 ZIP 다운로드"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = processing_jobs[job_id]
    if job['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Job not completed yet")

    zip_path = Path(job['zip_path'])
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        zip_path,
        media_type='application/zip',
        filename=f"ocr_results_{job_id}.zip"
    )


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='DeepSeek-OCR Standalone Web UI')
    parser.add_argument('--server', '-s', type=str, default=DEFAULT_SERVER_URL,
                       help=f'DeepSeek-OCR API server URL (default: {DEFAULT_SERVER_URL})')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT,
                       help=f'Local web UI port (default: {DEFAULT_PORT})')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not open browser automatically')

    args = parser.parse_args()

    # 전역 변수 설정
    global API_SERVER_URL
    API_SERVER_URL = args.server.rstrip('/')
    app.state.port = args.port

    # 브라우저 자동 열기
    if not args.no_browser:
        import threading
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f'http://localhost:{args.port}')
        threading.Thread(target=open_browser, daemon=True).start()

    # 서버 시작
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
