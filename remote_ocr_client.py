#!/usr/bin/env python3
"""
Remote OCR Client for DeepSeek-OCR API

This client allows you to process PDFs and images from your local machine
by sending them to a remote DeepSeek-OCR server and downloading the results.

Usage:
    # Process a single PDF
    python remote_ocr_client.py --server https://your-server.com:8000 --file document.pdf

    # Process multiple files
    python remote_ocr_client.py --server https://your-server.com:8000 --file file1.pdf file2.jpg file3.png

    # Process all PDFs in a folder
    python remote_ocr_client.py --server https://your-server.com:8000 --folder data/

    # Use custom prompt
    python remote_ocr_client.py --server https://your-server.com:8000 --file doc.pdf --prompt "<image>\nFree OCR."

    # Specify output directory
    python remote_ocr_client.py --server https://your-server.com:8000 --file doc.pdf --output results/
"""

import os
import sys
import argparse
import logging
import requests
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('remote_ocr_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    RESET = '\033[0m'


class RemoteOCRClient:
    """Client for processing files with remote DeepSeek-OCR API"""

    def __init__(self, server_url: str, output_dir: str = "ocr_results",
                 timeout: int = 300, api_key: Optional[str] = None):
        """
        Initialize the remote OCR client

        Args:
            server_url: URL of the remote DeepSeek-OCR server (e.g., https://server.com:8000)
            output_dir: Directory to save the OCR results
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
        """
        # Remove trailing slash from server URL
        self.server_url = server_url.rstrip('/')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.timeout = timeout
        self.api_key = api_key

        # Create subdirectories
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)

        # Test connection
        if not self._test_connection():
            raise ConnectionError(f"Cannot connect to server at {server_url}")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional API key"""
        headers = {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        return headers

    def _test_connection(self) -> bool:
        """Test if the remote server is accessible"""
        try:
            health_url = urljoin(self.server_url, '/health')
            response = requests.get(health_url, headers=self._get_headers(), timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✓ Connected to server: {self.server_url}")
                logger.info(f"  Model loaded: {health_data.get('model_loaded', 'unknown')}")
                logger.info(f"  CUDA available: {health_data.get('cuda_available', 'unknown')}")
                return True
            else:
                logger.error(f"✗ Server returned status code: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Connection failed: {str(e)}")
            return False

    def _determine_file_type(self, file_path: str) -> str:
        """Determine if file is PDF or image"""
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return 'pdf'
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
            return 'image'
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def process_file(self, file_path: str, custom_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Process a single file (PDF or image) with the remote OCR service

        Args:
            file_path: Path to the file to process
            custom_prompt: Optional custom prompt to use instead of server default

        Returns:
            Dictionary with processing results or None if failed
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            logger.error(f"✗ File not found: {file_path}")
            return None

        try:
            file_type = self._determine_file_type(file_path)
            endpoint = f'/ocr/{file_type}'
            url = urljoin(self.server_url, endpoint)

            logger.info(f"📤 Uploading {file_type}: {file_path_obj.name}")

            # Prepare the file for upload
            with open(file_path, 'rb') as f:
                files = {'file': (file_path_obj.name, f, self._get_mime_type(file_type))}

                # Add custom prompt if provided
                data = {}
                if custom_prompt:
                    data['prompt'] = custom_prompt
                    logger.info(f"   Using custom prompt: {custom_prompt[:50]}...")

                # Send request
                headers = self._get_headers()
                response = requests.post(url, files=files, data=data, headers=headers,
                                        timeout=self.timeout)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✓ Successfully processed: {file_path_obj.name}")
                    return {
                        'success': True,
                        'file_path': file_path,
                        'file_type': file_type,
                        'response': result
                    }
                else:
                    logger.error(f"✗ Server error ({response.status_code}): {response.text}")
                    return {
                        'success': False,
                        'file_path': file_path,
                        'error': f"Status {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"✗ Error processing {file_path}: {str(e)}")
            return {
                'success': False,
                'file_path': file_path,
                'error': str(e)
            }

    def _get_mime_type(self, file_type: str) -> str:
        """Get MIME type for file"""
        if file_type == 'pdf':
            return 'application/pdf'
        else:
            return 'image/jpeg'  # Generic image type

    def save_result(self, result: Dict[str, Any], output_suffix: str = "-OCR") -> Optional[str]:
        """
        Save OCR result to a markdown file

        Args:
            result: Result dictionary from process_file
            output_suffix: Suffix to add to output filename (default: -OCR)

        Returns:
            Path to saved markdown file or None if failed
        """
        if not result or not result.get('success'):
            return None

        try:
            file_path = Path(result['file_path'])
            response = result['response']

            # Generate output filename
            output_file = self.output_dir / f"{file_path.stem}{output_suffix}.md"

            # Extract content based on file type
            content = self._extract_content(response)

            if not content:
                logger.error(f"✗ No content to save for {file_path.name}")
                return None

            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"💾 Saved result to: {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"✗ Error saving result: {str(e)}")
            return None

    def _extract_content(self, response: Dict[str, Any]) -> str:
        """Extract markdown content from API response"""
        content_parts = []

        # Handle PDF response (multiple pages)
        if 'results' in response and isinstance(response['results'], list):
            for page_idx, page_result in enumerate(response['results']):
                if isinstance(page_result, dict) and 'result' in page_result:
                    page_content = page_result['result']
                    if page_content:
                        content_parts.append(f"## Page {page_idx + 1}\n\n{page_content}")

            return '\n\n<--- Page Split --->\n\n'.join(content_parts)

        # Handle single image response
        elif 'result' in response:
            return response['result']

        # Fallback: try common field names
        for field in ['markdown', 'content', 'text', 'output']:
            if field in response:
                return response[field]

        return json.dumps(response, indent=2, ensure_ascii=False)

    def process_batch(self, file_paths: List[str], custom_prompt: Optional[str] = None,
                     output_suffix: str = "-OCR") -> Dict[str, Any]:
        """
        Process multiple files and save results

        Args:
            file_paths: List of file paths to process
            custom_prompt: Optional custom prompt for all files
            output_suffix: Suffix for output filenames

        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'total': len(file_paths),
            'successful': 0,
            'failed': 0,
            'output_files': []
        }

        print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.CYAN}Processing {len(file_paths)} file(s){Colors.RESET}")
        print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")

        for idx, file_path in enumerate(file_paths, 1):
            print(f"{Colors.YELLOW}[{idx}/{len(file_paths)}]{Colors.RESET} Processing: {Colors.BLUE}{Path(file_path).name}{Colors.RESET}")

            # Process file
            result = self.process_file(file_path, custom_prompt)

            if result and result.get('success'):
                # Save result
                output_file = self.save_result(result, output_suffix)
                if output_file:
                    stats['successful'] += 1
                    stats['output_files'].append(output_file)
                    print(f"{Colors.GREEN}✓ Success{Colors.RESET}\n")
                else:
                    stats['failed'] += 1
                    print(f"{Colors.RED}✗ Failed to save result{Colors.RESET}\n")
            else:
                stats['failed'] += 1
                print(f"{Colors.RED}✗ Failed to process{Colors.RESET}\n")

        return stats

    def process_folder(self, folder_path: str, pattern: str = "*.pdf",
                      custom_prompt: Optional[str] = None, output_suffix: str = "-OCR") -> Dict[str, Any]:
        """
        Process all files matching pattern in a folder

        Args:
            folder_path: Path to folder containing files
            pattern: Glob pattern for files (default: "*.pdf")
            custom_prompt: Optional custom prompt for all files
            output_suffix: Suffix for output filenames

        Returns:
            Dictionary with processing statistics
        """
        folder = Path(folder_path)

        if not folder.exists() or not folder.is_dir():
            logger.error(f"✗ Folder not found: {folder_path}")
            return {'total': 0, 'successful': 0, 'failed': 0, 'output_files': []}

        # Find all matching files
        files = list(folder.glob(pattern))

        if not files:
            logger.warning(f"⚠ No files matching '{pattern}' found in {folder_path}")
            return {'total': 0, 'successful': 0, 'failed': 0, 'output_files': []}

        logger.info(f"📁 Found {len(files)} file(s) in {folder_path}")

        # Process all files
        return self.process_batch([str(f) for f in files], custom_prompt, output_suffix)


def load_config(config_file: str = "remote_config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    if not Path(config_file).exists():
        return {}

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}")
        return {}


def create_sample_config(config_file: str = "remote_config.yaml"):
    """Create a sample configuration file"""
    sample_config = {
        'server_url': 'http://localhost:8000',
        'api_key': None,
        'timeout': 300,
        'output_dir': 'ocr_results',
        'default_prompt': '<image>\n<|grounding|>Convert the document to markdown.',
        'output_suffix': '-OCR'
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(sample_config, f, default_flow_style=False, allow_unicode=True)

    print(f"{Colors.GREEN}✓ Created sample config file: {config_file}{Colors.RESET}")
    print(f"{Colors.YELLOW}  Please edit this file with your server details.{Colors.RESET}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Remote OCR Client for DeepSeek-OCR API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single PDF
  python remote_ocr_client.py --server https://server.com:8000 --file document.pdf

  # Process multiple files
  python remote_ocr_client.py --server https://server.com:8000 --file file1.pdf file2.jpg

  # Process all PDFs in a folder
  python remote_ocr_client.py --server https://server.com:8000 --folder data/

  # Use custom prompt
  python remote_ocr_client.py --server https://server.com:8000 --file doc.pdf \\
      --prompt "<image>\\nFree OCR."

  # Create sample config file
  python remote_ocr_client.py --create-config
        """
    )

    parser.add_argument('--server', '-s', type=str,
                       help='Remote server URL (e.g., https://server.com:8000)')
    parser.add_argument('--file', '-f', type=str, nargs='+',
                       help='File(s) to process')
    parser.add_argument('--folder', '-d', type=str,
                       help='Folder containing files to process')
    parser.add_argument('--pattern', '-p', type=str, default='*.pdf',
                       help='File pattern for folder processing (default: *.pdf)')
    parser.add_argument('--prompt', type=str,
                       help='Custom prompt to use')
    parser.add_argument('--output', '-o', type=str, default='ocr_results',
                       help='Output directory (default: ocr_results)')
    parser.add_argument('--suffix', type=str, default='-OCR',
                       help='Output file suffix (default: -OCR)')
    parser.add_argument('--timeout', '-t', type=int, default=300,
                       help='Request timeout in seconds (default: 300)')
    parser.add_argument('--api-key', '-k', type=str,
                       help='API key for authentication')
    parser.add_argument('--config', '-c', type=str, default='remote_config.yaml',
                       help='Config file path (default: remote_config.yaml)')
    parser.add_argument('--create-config', action='store_true',
                       help='Create a sample config file and exit')

    args = parser.parse_args()

    # Handle config file creation
    if args.create_config:
        create_sample_config(args.config)
        return

    # Load config file
    config = load_config(args.config)

    # Merge command line args with config (CLI args take precedence)
    server_url = args.server or config.get('server_url')
    api_key = args.api_key or config.get('api_key')
    timeout = args.timeout if args.timeout != 300 else config.get('timeout', 300)
    output_dir = args.output if args.output != 'ocr_results' else config.get('output_dir', 'ocr_results')
    custom_prompt = args.prompt or config.get('default_prompt')
    output_suffix = args.suffix if args.suffix != '-OCR' else config.get('output_suffix', '-OCR')

    # Validate required arguments
    if not server_url:
        parser.error("Server URL is required. Use --server or set it in config file.")

    if not args.file and not args.folder:
        parser.error("Either --file or --folder must be specified.")

    # Print header
    print(f"\n{Colors.MAGENTA}{'='*70}{Colors.RESET}")
    print(f"{Colors.MAGENTA}DeepSeek-OCR Remote Client{Colors.RESET}")
    print(f"{Colors.MAGENTA}{'='*70}{Colors.RESET}")
    print(f"{Colors.CYAN}Server: {Colors.RESET}{server_url}")
    print(f"{Colors.CYAN}Output: {Colors.RESET}{output_dir}")
    if custom_prompt:
        print(f"{Colors.CYAN}Prompt: {Colors.RESET}{custom_prompt[:50]}...")
    print(f"{Colors.MAGENTA}{'='*70}{Colors.RESET}\n")

    try:
        # Initialize client
        client = RemoteOCRClient(
            server_url=server_url,
            output_dir=output_dir,
            timeout=timeout,
            api_key=api_key
        )

        # Process files
        if args.file:
            stats = client.process_batch(args.file, custom_prompt, output_suffix)
        else:
            stats = client.process_folder(args.folder, args.pattern, custom_prompt, output_suffix)

        # Print summary
        print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.CYAN}Processing Summary{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"Total files:  {stats['total']}")
        print(f"{Colors.GREEN}Successful:   {stats['successful']}{Colors.RESET}")
        print(f"{Colors.RED}Failed:       {stats['failed']}{Colors.RESET}")

        if stats['output_files']:
            print(f"\n{Colors.CYAN}Output files:{Colors.RESET}")
            for output_file in stats['output_files']:
                print(f"  {Colors.GREEN}✓{Colors.RESET} {output_file}")

        print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        print(f"\n{Colors.RED}✗ Error: {str(e)}{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
