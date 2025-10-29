# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepSeek-OCR Dockerized API is a GPU-accelerated OCR service that converts PDFs and images to Markdown using the DeepSeek-OCR model with vLLM backend. The project provides both a FastAPI REST API (Docker-based) and standalone Python batch processors for local PDF conversion.

## Critical Information: Custom File Replacements

**IMPORTANT**: This project includes custom files that patch critical bugs in the original DeepSeek-OCR library. During Docker build, these custom files transparently replace the originals:

- [custom_config.py](custom_config.py) → replaces `config.py` (customizable prompt defaults)
- [custom_image_process.py](custom_image_process.py) → replaces `process/image_process.py` (fixes missing prompt parameter bug)
- [custom_deepseek_ocr.py](custom_deepseek_ocr.py) → replaces `deepseek_ocr.py`
- [custom_run_dpsk_ocr_pdf.py](custom_run_dpsk_ocr_pdf.py) → replaces `run_dpsk_ocr_pdf.py`
- [custom_run_dpsk_ocr_image.py](custom_run_dpsk_ocr_image.py) → replaces `run_dpsk_ocr_image.py`
- [custom_run_dpsk_ocr_eval_batch.py](custom_run_dpsk_ocr_eval_batch.py) → replaces `run_dpsk_ocr_eval_batch.py`

**Critical Bug Fixed**: The original DeepSeek-OCR library calls `tokenize_with_images()` without the required `prompt` parameter during model initialization, causing server startup failures. The custom files fix this issue.

## System Requirements

### Hardware
- **NVIDIA GPU** with CUDA 11.8+ support
- **GPU Memory**: Minimum 12GB VRAM (model uses ~9GB)
- **System RAM**: Minimum 32GB recommended (64GB+ for production)
- **Storage**: 50GB+ free space for model weights and containers

### Software
- **Docker** 20.10+ with GPU support
- **Docker Compose** 2.0+
- **NVIDIA Container Toolkit** installed
- **Python 3.8+** (for local batch processors)

## Common Development Commands

### Docker Setup and Management

```bash
# Build the Docker image (Windows)
build.bat

# Build the Docker image (Linux/macOS)
docker-compose build

# Force rebuild without cache (if custom files were updated)
docker builder prune -f
docker-compose build --no-cache

# Start the OCR service
docker-compose up -d

# View logs
docker-compose logs -f deepseek-ocr

# Stop the service
docker-compose down

# Check service health
curl http://localhost:8000/health

# Access container shell for debugging
docker-compose run --rm deepseek-ocr bash
```

### Model Setup

```bash
# Create models directory
mkdir -p models

# Download model weights using Hugging Face CLI
pip install huggingface_hub
huggingface-cli download deepseek-ai/DeepSeek-OCR --local-dir models/deepseek-ai/DeepSeek-OCR

# Alternative: Clone using git
git clone https://huggingface.co/deepseek-ai/DeepSeek-OCR models/deepseek-ai/DeepSeek-OCR
```

### Batch PDF Processing

```bash
# Place PDFs in data/ directory
cp your_document.pdf data/

# Basic markdown conversion
python pdf_to_markdown_processor.py

# Enhanced markdown with image extraction
python pdf_to_markdown_processor_enhanced.py

# Plain OCR text extraction (no markdown formatting)
python pdf_to_ocr_enhanced.py

# Custom prompt processing (edit custom_prompt.yaml first)
python pdf_to_custom_prompt.py
python pdf_to_custom_prompt_enhanced.py
```

### API Testing

```bash
# Process single image
curl -X POST "http://localhost:8000/ocr/image" \
  -F "file=@image.jpg"

# Process PDF
curl -X POST "http://localhost:8000/ocr/pdf" \
  -F "file=@document.pdf"

# Process with custom prompt
curl -X POST "http://localhost:8000/ocr/pdf" \
  -F "file=@document.pdf" \
  -F "prompt=<image>\n<|grounding|>Extract all tables."

# Batch processing
curl -X POST "http://localhost:8000/ocr/batch" \
  -F "files=@image1.jpg" \
  -F "files=@document.pdf"
```

### Remote Server Usage

Three ways to use remote server:

**1. Web UI (Recommended for most users)**:
```bash
# Run standalone Web UI on local PC
python webui/webui_standalone.py --server https://your-server.com

# Browser opens automatically at http://localhost:8080
# Drag & drop files → Process → Download ZIP
# See webui/WEBUI_STANDALONE_GUIDE.md
```

**2. Command Line Client (For automation)**:
```bash
# Create config file
python remote_ocr_client.py --create-config

# Process files
python remote_ocr_client.py --server https://your-server.com --file document.pdf
python remote_ocr_client.py --server https://your-server.com --folder data/

# See REMOTE_SERVER_GUIDE.md
```

**3. Direct API Calls (For developers)**:
```bash
curl -X POST "https://your-server.com/ocr/pdf" -F "file=@document.pdf"
```

## Architecture Overview

### Core Components

1. **FastAPI Server** ([start_server.py](start_server.py))
   - REST API endpoints for OCR processing
   - Handles image and PDF uploads
   - Supports custom prompts via API parameters
   - Uses vLLM for GPU-accelerated inference
   - Model initialization happens on startup

2. **Batch Processors** (pdf_to_*.py files)
   - Standalone Python scripts for local PDF processing
   - Scan `data/` directory for PDFs
   - Call the FastAPI backend (requires Docker service running)
   - Different processors use different prompts and post-processing

3. **Custom Configuration** ([custom_config.py](custom_config.py))
   - Defines default prompt, model settings, image processing parameters
   - `PROMPT` variable sets the default prompt (can be overridden via API)
   - `CROP_MODE`, `BASE_SIZE`, `IMAGE_SIZE` control image preprocessing
   - `MAX_CONCURRENCY` controls GPU memory usage

### Processing Flow

```
User Request (PDF/Image)
    ↓
FastAPI Endpoint (/ocr/pdf or /ocr/image)
    ↓
Image Preprocessing (DeepseekOCRProcessor.tokenize_with_images)
    ↓
vLLM Inference (GPU-accelerated generation)
    ↓
Post-processing (token cleanup, page splitting)
    ↓
Return Markdown/OCR Result
```

### Output File Naming Convention

Batch processors append suffixes to indicate processing method:
- `-MD.md`: Markdown conversion (document structure preserved)
- `-OCR.md`: Plain OCR extraction (raw text without formatting)
- `-CUSTOM.md`: Custom prompt processing (from custom_prompt.yaml)

Example: `document.pdf` → `document-MD.md`, `document-OCR.md`, `document-CUSTOM.md`

## Configuration and Customization

### Default Prompt Customization

Edit [custom_config.py](custom_config.py):

```python
# Change the default prompt used by the API
PROMPT = '<image>\n<|grounding|>Convert the document to markdown.'

# Common alternatives:
# PROMPT = '<image>\nFree OCR.'  # Plain text without formatting
# PROMPT = '<image>\n<|grounding|>OCR this image.'  # For non-document images
# PROMPT = '<image>\nParse the figure.'  # For extracting figures
```

After editing, rebuild the Docker container to apply changes:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Custom Prompts for Batch Processing

Edit [custom_prompt.yaml](custom_prompt.yaml):

```yaml
prompt: |-
  <image>
  <|grounding|>Your custom prompt here.
```

Then run: `python pdf_to_custom_prompt_enhanced.py`

### Performance Tuning

Edit [docker-compose.yml](docker-compose.yml):

```yaml
environment:
  - MAX_CONCURRENCY=5          # Lower for less GPU memory
  - GPU_MEMORY_UTILIZATION=0.85  # Adjust based on GPU capacity (0.1-1.0)
  - CUDA_VISIBLE_DEVICES=0      # GPU device ID
```

**Recommendations**:
- High-throughput: `MAX_CONCURRENCY=100`, `GPU_MEMORY_UTILIZATION=0.95`
- Memory-constrained: `MAX_CONCURRENCY=10`, `GPU_MEMORY_UTILIZATION=0.7`

## Prompt Format Reference

DeepSeek-OCR supports special tokens in prompts:

- `<image>` - Required at the start of every prompt
- `<|grounding|>` - Enables layout-aware processing (preserves document structure)
- `<|ref|>...<|/ref|>` - For locating specific text in images

**Common Prompt Patterns**:
- Document to Markdown: `<image>\n<|grounding|>Convert the document to markdown.`
- Plain OCR: `<image>\nFree OCR.`
- Image OCR: `<image>\n<|grounding|>OCR this image.`
- Figure parsing: `<image>\nParse the figure.`
- General description: `<image>\nDescribe this image in detail.`

## Troubleshooting

### Docker Build Issues

**Problem**: Build fails with missing files
```bash
# Ensure DeepSeek-OCR source exists
ls DeepSeek-OCR/DeepSeek-OCR-master/

# Re-clone if missing
git clone https://github.com/deepseek-ai/DeepSeek-OCR
```

**Problem**: Custom files not applied
```bash
# Force rebuild without cache
docker builder prune -f
docker-compose build --no-cache
```

### Runtime Issues

**Problem**: Out of memory errors
- Lower `MAX_CONCURRENCY` in docker-compose.yml
- Reduce `GPU_MEMORY_UTILIZATION` to 0.7 or lower
- Close other GPU processes

**Problem**: Server startup fails with "missing 1 required positional argument: 'prompt'"
- This is the bug fixed by custom files
- Verify custom files exist: `ls custom_*.py`
- Rebuild with `--no-cache` to ensure replacements are applied

**Problem**: Model not found
```bash
# Check model directory structure
ls -la models/deepseek-ai/DeepSeek-OCR/

# Verify model mounted correctly
docker-compose exec deepseek-ocr ls -la /app/models/deepseek-ai/DeepSeek-OCR/
```

### API Issues

**Problem**: Cannot connect to API
```bash
# Check if container is running
docker-compose ps

# Check logs for errors
docker-compose logs -f deepseek-ocr

# Verify health endpoint
curl http://localhost:8000/health
```

**Problem**: Slow processing
```bash
# Monitor GPU usage
nvidia-smi -l 1

# Check if model is loaded
curl http://localhost:8000/health | grep model_loaded
```

## Development Notes

### When Modifying Custom Files

If you edit any `custom_*.py` files, you MUST rebuild the Docker container for changes to take effect:

```bash
docker-compose down
docker builder prune -f
docker-compose build --no-cache
docker-compose up -d
```

### Adding New Batch Processors

When creating new PDF processors:
1. Import the API client logic from existing processors
2. Use appropriate prompt for the use case
3. Follow the naming convention: `pdf_to_<purpose>.py`
4. Output files with descriptive suffix: `-<PURPOSE>.md`
5. Place PDFs in `data/` directory, write outputs to same location

### Testing Changes

```bash
# Test API health
curl http://localhost:8000/health

# Test with sample image
curl -X POST "http://localhost:8000/ocr/image" -F "file=@test.jpg"

# Run batch processor
python pdf_to_markdown_processor.py
```

## File Structure Reference

```text
.
├── custom_*.py                      # Custom patches (replace originals during build)
├── start_server.py                  # FastAPI server entrypoint (API only)
├── webui_standalone.py              # Standalone Web UI (run locally)
├── remote_ocr_client.py             # Command-line client for remote usage
├── pdf_to_markdown_processor.py     # Basic markdown batch processor
├── pdf_to_markdown_processor_enhanced.py  # Enhanced with image extraction
├── pdf_to_ocr_enhanced.py           # Plain OCR batch processor
├── pdf_to_custom_prompt.py          # Custom prompt batch processor
├── pdf_to_custom_prompt_enhanced.py # Custom prompt with enhancements
├── custom_prompt.yaml               # Custom prompt configuration
├── remote_config.yaml.example       # Sample remote client config
├── Dockerfile                       # Container definition (API server)
├── docker-compose.yml               # Service configuration
├── build.bat                        # Windows build script
├── REMOTE_SERVER_GUIDE.md           # Remote server setup guide
├── webui/WEBUI_STANDALONE_GUIDE.md        # Web UI standalone usage guide
├── data/                            # PDF input/output directory
│   └── images/                      # Extracted images (enhanced processors)
└── models/                          # Model weights (mounted as volume)
    └── deepseek-ai/DeepSeek-OCR/
```

## Important Constraints

- **GPU Required**: This project requires an NVIDIA GPU with CUDA support. CPU-only operation is not supported.
- **Model Size**: The DeepSeek-OCR model is large (~9GB GPU memory). Ensure sufficient GPU capacity.
- **Docker Dependency**: Batch processors require the Docker service to be running at localhost:8000.
- **Windows Compatibility**: Windows users must use WSL2-based Docker Desktop with GPU support enabled.

## Environment-Specific Notes

### Windows
- Use `build.bat` for building
- Ensure WSL2 backend is enabled in Docker Desktop
- NVIDIA Container Toolkit must be installed in WSL2

### Linux
- Ensure NVIDIA drivers and Container Toolkit are installed
- Use `docker-compose build` directly

### macOS
- This project is not compatible with macOS (requires NVIDIA GPU)
