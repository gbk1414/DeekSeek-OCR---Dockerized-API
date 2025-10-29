#!/usr/bin/env python3
"""
DeepSeek-OCR Web UI
A simple web interface for batch OCR processing with file upload and ZIP download
"""

import os
import sys
import io
import shutil
import asyncio
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add DeepSeek-OCR to path
sys.path.insert(0, '/app/DeepSeek-OCR-vllm')

# Import from start_server
from start_server import (
    llm, sampling_params, initialize_model,
    pdf_to_images_high_quality, process_single_image,
    PROMPT
)

# Create FastAPI app
app = FastAPI(
    title="DeepSeek-OCR Web UI",
    description="Web interface for batch OCR processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage for processing jobs
UPLOAD_DIR = Path("/app/webui_uploads")
RESULTS_DIR = Path("/app/webui_results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Job tracking
processing_jobs = {}


def cleanup_old_files():
    """Clean up files older than 24 hours"""
    import time
    current_time = time.time()
    max_age = 24 * 3600  # 24 hours

    for directory in [UPLOAD_DIR, RESULTS_DIR]:
        for item in directory.iterdir():
            if item.is_file() or item.is_dir():
                if current_time - item.stat().st_mtime > max_age:
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    except Exception:
                        pass


async def process_files_batch(job_id: str, files: List[Path], custom_prompt: Optional[str] = None):
    """Process multiple files and create a ZIP archive"""
    try:
        # Update job status
        processing_jobs[job_id]['status'] = 'processing'
        processing_jobs[job_id]['total'] = len(files)
        processing_jobs[job_id]['processed'] = 0

        # Create results directory for this job
        job_results_dir = RESULTS_DIR / job_id
        job_results_dir.mkdir(exist_ok=True)

        use_prompt = custom_prompt if custom_prompt else PROMPT

        # Process each file
        for idx, file_path in enumerate(files):
            try:
                processing_jobs[job_id]['current_file'] = file_path.name

                # Determine file type
                ext = file_path.suffix.lower()

                if ext == '.pdf':
                    # Process PDF
                    images = pdf_to_images_high_quality(file_path.read_bytes(), dpi=144)

                    markdown_content = ""
                    for page_idx, image in enumerate(images):
                        result = process_single_image(image, use_prompt)
                        markdown_content += f"## Page {page_idx + 1}\n\n{result}\n\n<--- Page Split --->\n\n"

                    # Save result
                    output_file = job_results_dir / f"{file_path.stem}.md"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(markdown_content.strip())

                elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                    # Process image
                    from PIL import Image
                    image = Image.open(file_path).convert('RGB')
                    result = process_single_image(image, use_prompt)

                    # Save result
                    output_file = job_results_dir / f"{file_path.stem}.md"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(result)

                processing_jobs[job_id]['processed'] = idx + 1
                processing_jobs[job_id]['successful'] += 1

            except Exception as e:
                processing_jobs[job_id]['failed'] += 1
                processing_jobs[job_id]['errors'].append(f"{file_path.name}: {str(e)}")

        # Create ZIP file
        zip_path = RESULTS_DIR / f"{job_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for md_file in job_results_dir.glob("*.md"):
                zipf.write(md_file, md_file.name)

        # Update job status
        processing_jobs[job_id]['status'] = 'completed'
        processing_jobs[job_id]['zip_path'] = str(zip_path)
        processing_jobs[job_id]['completed_at'] = datetime.now().isoformat()

    except Exception as e:
        processing_jobs[job_id]['status'] = 'failed'
        processing_jobs[job_id]['error'] = str(e)


@app.on_event("startup")
async def startup_event():
    """Initialize the model on startup"""
    initialize_model()
    cleanup_old_files()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI"""
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeepSeek-OCR Web UI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
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

        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
        }

        .content {
            padding: 30px;
        }

        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            background: #f8f9ff;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .upload-area:hover {
            border-color: #764ba2;
            background: #f0f1ff;
        }

        .upload-area.dragover {
            border-color: #764ba2;
            background: #e8e9ff;
            transform: scale(1.02);
        }

        .upload-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }

        input[type="file"] {
            display: none;
        }

        .file-list {
            margin-top: 20px;
            max-height: 300px;
            overflow-y: auto;
        }

        .file-item {
            background: #f8f9fa;
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .file-item .name {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .file-item .size {
            color: #6c757d;
            font-size: 0.9em;
            margin-left: 10px;
        }

        .file-item .remove {
            background: #dc3545;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }

        .file-item .remove:hover {
            background: #c82333;
        }

        .prompt-section {
            margin-top: 30px;
        }

        .prompt-section label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }

        .prompt-section textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
        }

        .prompt-section textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .buttons {
            margin-top: 30px;
            display: flex;
            gap: 12px;
        }

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

        .btn-secondary {
            background: #6c757d;
            color: white;
        }

        .btn-secondary:hover {
            background: #5a6268;
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .progress-section {
            margin-top: 30px;
            display: none;
        }

        .progress-section.active {
            display: block;
        }

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

        .status-text {
            text-align: center;
            color: #666;
            margin-bottom: 16px;
        }

        .download-section {
            margin-top: 20px;
            padding: 20px;
            background: #d4edda;
            border-radius: 8px;
            border: 2px solid #c3e6cb;
            text-align: center;
        }

        .download-section h3 {
            color: #155724;
            margin-bottom: 12px;
        }

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

        .download-btn:hover {
            background: #218838;
        }

        .error-section {
            margin-top: 20px;
            padding: 20px;
            background: #f8d7da;
            border-radius: 8px;
            border: 2px solid #f5c6cb;
        }

        .error-section h4 {
            color: #721c24;
            margin-bottom: 12px;
        }

        .error-list {
            color: #721c24;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 DeepSeek-OCR Web UI</h1>
            <p>PDF 및 이미지 파일을 업로드하여 OCR 처리 후 결과를 ZIP으로 다운로드하세요</p>
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
                <textarea id="promptInput" rows="3" placeholder="기본값: <image>\n<|grounding|>Convert the document to markdown."></textarea>
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

        // File upload handlers
        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

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

            // Prepare form data
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });

            const customPrompt = document.getElementById('promptInput').value.trim();
            if (customPrompt) {
                formData.append('prompt', customPrompt);
            }

            // Disable buttons
            processBtn.disabled = true;
            progressSection.classList.add('active');
            downloadSection.innerHTML = '';
            errorSection.innerHTML = '';

            try {
                const response = await fetch('/webui/process', {
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
                const response = await fetch(`/webui/status/${jobId}`);
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
                            <a href="/webui/download/${jobId}" class="download-btn" download>📥 결과 다운로드 (ZIP)</a>
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
</html>
    """
    return HTMLResponse(content=html_content)


@app.post("/webui/process")
async def webui_process(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    prompt: Optional[str] = Form(None)
):
    """Process uploaded files"""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Generate job ID
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # Create upload directory for this job
    job_upload_dir = UPLOAD_DIR / job_id
    job_upload_dir.mkdir(exist_ok=True)

    # Save uploaded files
    file_paths = []
    for file in files:
        file_path = job_upload_dir / file.filename
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        file_paths.append(file_path)

    # Initialize job tracking
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

    # Start background processing
    background_tasks.add_task(process_files_batch, job_id, file_paths, prompt)

    return {"job_id": job_id, "total_files": len(file_paths)}


@app.get("/webui/status/{job_id}")
async def webui_status(job_id: str):
    """Get job status"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return processing_jobs[job_id]


@app.get("/webui/download/{job_id}")
async def webui_download(job_id: str):
    """Download processed results as ZIP"""
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


if __name__ == "__main__":
    print("Starting DeepSeek-OCR Web UI on port 8001...")
    uvicorn.run(
        "webui:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        workers=1
    )
