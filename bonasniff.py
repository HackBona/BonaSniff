import os
import re
import sys
import time
import json
import queue
import random
import threading
import requests
import mimetypes
from urllib.parse import urlparse, urljoin, unquote
from bs4 import BeautifulSoup
from collections import defaultdict
import shutil
import webbrowser
import platform
import subprocess
try:
    import pyqrcode
except ImportError:
    pass

# Initialize mimetypes
mimetypes.init()

# Enhanced ASCII Banner
BANNER = r"""
███████╗ █████╗ ██████╗ ██████╗  ██████╗ ███╗   ██╗ █████╗     ███████╗ ██████╗ █████╗ ███╗   ██╗
██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔═══██╗████╗  ██║██╔══██╗    ██╔════╝██╔════╝██╔══██╗████╗  ██║
███████╗███████║██████╔╝██████╔╝██║   ██║██╔██╗ ██║███████║    ███████╗██║     ███████║██╔██╗ ██║
╚════██║██╔══██║██╔══██╗██╔══██╗██║   ██║██║╚██╗██║██╔══██║    ╚════██║██║     ██╔══██║██║╚██╗██║
███████║██║  ██║██████╔╝██████╔╝╚██████╔╝██║ ╚████║██║  ██║    ███████║╚██████╗██║  ██║██║ ╚████║
╚══════╝╚═╝  ╚═╝╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝
"""

# Gradient Color Palette
COLOR_BANNER = "\033[38;2;255;105;180m"  # Hot pink
COLOR_PRIMARY = "\033[38;2;0;191;255m"    # Deep sky blue
COLOR_SUCCESS = "\033[38;2;50;205;50m"    # Lime green
COLOR_WARNING = "\033[38;2;255;215;0m"    # Gold
COLOR_ERROR = "\033[38;2;255;69;0m"       # Red-orange
COLOR_HIGHLIGHT = "\033[38;2;138;43;226m" # Blue violet
COLOR_ACCENT = "\033[38;2;255;165;0m"     # Orange
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_DONATE = "\033[38;2;255;215;0m"    # Gold for donation emphasis
COLOR_SUPPORT = "\033[38;2;255;105;180m"  # Pink for support messages

# Common user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
]

class SabbonaScanner:
    def __init__(self, base_url, output_dir=None, max_depth=5, max_pages=500, verbose=False, preserve_structure=True):
        self.base_url = self.normalize_url(base_url)
        self.domain = urlparse(self.base_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.verbose = verbose
        self.preserve_structure = preserve_structure
        self.visited = set()
        self.to_visit = queue.Queue()
        self.to_visit.put((self.base_url, 0))  # (url, depth)
        self.file_tree = defaultdict(list)
        self.session = requests.Session()
        self.root_folder = output_dir or f"sabbona_scan_{self.domain}"
        self.start_time = time.time()
        self.page_count = 0
        self.asset_count = 0
        self.error_count = 0
        self.running = True
        
        # Configure session with rotating user agents
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'TE': 'trailers'
        })
        
    @staticmethod
    def normalize_url(url):
        """Ensure URL has proper scheme and format"""
        if not url.startswith(('http://', 'https://')):
            return 'https://' + url
        return url
    
    def log(self, message, level="info", prefix=""):
        """Enhanced log messages with modern styling"""
        styles = {
            "info": (COLOR_PRIMARY, "ℹ"),
            "success": (COLOR_SUCCESS, "✓"),
            "warning": (COLOR_WARNING, "⚠"),
            "error": (COLOR_ERROR, "✗"),
            "header": (COLOR_BANNER, "◆"),
            "bold": (COLOR_HIGHLIGHT, "➤")
        }
        
        color, icon = styles.get(level, (COLOR_RESET, "•"))
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        
        if prefix:
            prefix = f"{COLOR_ACCENT}{prefix}{COLOR_RESET} "
            
        print(f"{COLOR_BOLD}{COLOR_ACCENT}[{timestamp}]{COLOR_RESET} {color}{icon}{COLOR_RESET} {prefix}{message}")
        sys.stdout.flush()
    
    def print_header(self):
        """Print stylish header with gradient text"""
        terminal_width = shutil.get_terminal_size().columns
        header_text = "SabbonaScan - Professional Website Scanner"
        developer_text = "Developed by Sabbona Tessema"
        
        # Create gradient effect for header
        gradient_header = ""
        for i, char in enumerate(header_text):
            r = int(255 * (i / len(header_text)))
            g = int(191 * (1 - i / len(header_text)))
            b = 255
            gradient_header += f"\033[38;2;{r};{g};{b}m{char}"
        
        # Center content
        banner_lines = BANNER.strip().split('\n')
        max_banner_width = max(len(line) for line in banner_lines)
        
        print()
        for line in banner_lines:
            padding = (terminal_width - max_banner_width) // 2
            print(" " * padding + f"{COLOR_BANNER}{line}{COLOR_RESET}")
        
        print("\n" + " " * ((terminal_width - len(header_text)) // 2) + 
              f"{gradient_header}{COLOR_RESET}")
        print(" " * ((terminal_width - len(developer_text)) // 2) + 
              f"{COLOR_HIGHLIGHT}{developer_text}{COLOR_RESET}\n")
        print("-" * terminal_width)
    
    def create_folder_structure(self):
        """Create organized folder structure with logging"""
        # We'll create the root folder only
        os.makedirs(self.root_folder, exist_ok=True)
        if self.verbose:
            self.log(f"Created directory: {self.root_folder}", "info", "FOLDER")
    
    def sanitize_filename(self, name):
        """Create safe filename from string"""
        return re.sub(r'[^a-zA-Z0-9\-_\.]', '_', name)
    
    def generate_file_path(self, url, category):
        """
        Generate file path while preserving website structure
        Returns: (file_path, relative_path)
        """
        parsed = urlparse(url)
        path = parsed.path
        
        # Handle root path
        if not path or path == '/':
            return os.path.join(self.root_folder, "index.html"), "index.html"
        
        # Split path into components
        path_parts = path.strip('/').split('/')
        sanitized_parts = [self.sanitize_filename(part) for part in path_parts]
        
        # Handle directory paths (end with slash)
        if url.endswith('/') or not path_parts[-1].count('.'):
            sanitized_parts.append('index.html')
        
        # Create relative path preserving structure
        relative_path = os.path.join(*sanitized_parts)
        full_path = os.path.join(self.root_folder, relative_path)
        
        return full_path, relative_path
    
    def get_file_category(self, url, content_type):
        """Categorize files based on extension or content type"""
        # Try to get from extension first
        parsed = urlparse(url)
        path = parsed.path
        filename = os.path.basename(path)
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in ['.html', '.htm']:
            return 'html', 'HTML File'
        elif ext in ['.css']:
            return 'css', 'CSS File'
        elif ext in ['.js']:
            return 'js', 'JavaScript'
        elif ext in ['.php', '.phtml']:
            return 'php', 'PHP Script'
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp']:
            return 'images', 'Image'
        elif ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']:
            return 'fonts', 'Font'
        elif ext in ['.mp4', '.webm', '.mp3', '.wav', '.ogg', '.flac', '.mov']:
            return 'media', 'Media'
        elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            return 'other', 'Document'
        elif ext in ['.zip', '.tar', '.gz', '.7z', '.rar']:
            return 'other', 'Archive'
        
        # Fallback to content type
        if 'text/html' in content_type:
            return 'html', 'HTML File'
        elif 'text/css' in content_type:
            return 'css', 'CSS File'
        elif 'javascript' in content_type:
            return 'js', 'JavaScript'
        elif 'php' in content_type or 'x-php' in content_type:
            return 'php', 'PHP Script'
        elif 'image/' in content_type:
            return 'images', 'Image'
        elif 'font/' in content_type or 'application/font' in content_type:
            return 'fonts', 'Font'
        elif 'video/' in content_type or 'audio/' in content_type:
            return 'media', 'Media'
        elif 'application/pdf' in content_type:
            return 'other', 'PDF Document'
        elif 'application/msword' in content_type or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            return 'other', 'Word Document'
        elif 'application/vnd.ms-excel' in content_type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
            return 'other', 'Excel Document'
        
        # Special handling for assets
        if '/assets/' in url.lower() or '/static/' in url.lower():
            if ext in ['.css'] or 'text/css' in content_type:
                return 'assets/css', 'CSS Asset'
            elif ext in ['.js'] or 'javascript' in content_type:
                return 'assets/js', 'JavaScript Asset'
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico'] or 'image/' in content_type:
                return 'assets/images', 'Image Asset'
        
        return 'other', 'Other'
    
    def process_url(self, url, depth):
        """Download and process a single URL with retries"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Rotate user agent
                self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                
                # Add referer header to appear more like a browser
                headers = {'Referer': self.base_url} if depth > 0 else {}
                
                response = self.session.get(url, headers=headers, timeout=15)
                
                # Handle HTTP errors
                if response.status_code != 200:
                    self.error_count += 1
                    self.log(f"HTTP Error {response.status_code} for {url} (attempt {attempt+1}/{max_retries})", "warning", "HTTP")
                    
                    # If it's a 403 and we have retries left, try again
                    if response.status_code == 403 and attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None
                
                # Get content type
                content_type = response.headers.get('Content-Type', '').lower()
                
                # Determine file category
                category, file_type = self.get_file_category(url, content_type)
                
                # Generate file path preserving website structure
                file_path, relative_path = self.generate_file_path(url, category)
                
                # Create subdirectories if needed
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                self.asset_count += 1
                self.log(f"Downloaded: {url} -> {file_path}", "success", file_type.upper())
                
                # Parse HTML for links
                links = []
                if 'text/html' in content_type:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find all links
                    for tag in soup.find_all(['a', 'link'], href=True):
                        href = tag.get('href')
                        if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                            absolute_url = urljoin(url, href)
                            if urlparse(absolute_url).netloc == self.domain:
                                links.append(absolute_url)
                    
                    # Find all resources
                    for tag in soup.find_all(['script', 'img', 'source', 'audio', 'video', 'iframe'], src=True):
                        src = tag.get('src')
                        if src:
                            absolute_url = urljoin(url, src)
                            if urlparse(absolute_url).netloc == self.domain:
                                links.append(absolute_url)
                    
                    # Find all CSS resources
                    for tag in soup.find_all('link', rel='stylesheet'):
                        href = tag.get('href')
                        if href:
                            absolute_url = urljoin(url, href)
                            if urlparse(absolute_url).netloc == self.domain:
                                links.append(absolute_url)
                    
                    # Find all CSS imports in style tags
                    for style in soup.find_all('style'):
                        if style.string:
                            # Find url() patterns in CSS
                            css_urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style.string)
                            for css_url in css_urls:
                                absolute_url = urljoin(url, css_url)
                                if urlparse(absolute_url).netloc == self.domain:
                                    links.append(absolute_url)
                    
                    # Find all meta refresh redirects
                    for meta in soup.find_all('meta', attrs={'http-equiv': re.compile('^refresh$', re.I)}):
                        if 'content' in meta.attrs:
                            content = meta.attrs['content']
                            match = re.search(r'url=(.+)', content, re.I)
                            if match:
                                redirect_url = match.group(1)
                                absolute_url = urljoin(url, redirect_url)
                                if urlparse(absolute_url).netloc == self.domain:
                                    links.append(absolute_url)
                
                return {
                    'path': file_path,
                    'relative_path': relative_path,
                    'links': links,
                    'category': category,
                    'type': file_type
                }
                
            except Exception as e:
                self.error_count += 1
                self.log(f"Error processing {url} (attempt {attempt+1}/{max_retries}): {str(e)}", "error", "ERROR")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None
        return None
    
    def crawl(self):
        """Crawl the website with breadth-first search"""
        self.print_header()
        self.log("Starting deep website scan...", "header")
        self.log(f"Target: {COLOR_BOLD}{self.base_url}{COLOR_RESET}", "bold")
        self.log(f"Max Depth: {COLOR_ACCENT}{self.max_depth}{COLOR_RESET}, Max Pages: {COLOR_ACCENT}{self.max_pages}{COLOR_RESET}", "info")
        self.log(f"Output Directory: {COLOR_ACCENT}{os.path.abspath(self.root_folder)}{COLOR_RESET}", "info")
        self.log(f"Folder Structure: {'PRESERVED' if self.preserve_structure else 'CATEGORIZED'}", "info")
        self.log("-" * shutil.get_terminal_size().columns, "info")
        
        self.create_folder_structure()
        
        # Animation characters for loading effect
        animation = "⣾⣽⣻⢿⡿⣟⣯⣷"
        anim_index = 0
        
        while not self.to_visit.empty() and self.running and self.page_count < self.max_pages:
            url, depth = self.to_visit.get()
            
            if url in self.visited:
                continue
                
            self.visited.add(url)
            self.page_count += 1
            
            # Enhanced progress display
            terminal_width = shutil.get_terminal_size().columns
            progress = (self.page_count / self.max_pages) * 100
            progress_bar_width = max(20, terminal_width - 50)
            filled = int(progress_bar_width * self.page_count // self.max_pages)
            progress_bar = f"{COLOR_SUCCESS}{'█' * filled}{COLOR_RESET}{'░' * (progress_bar_width - filled)}"
            
            # Animation
            anim_char = animation[anim_index % len(animation)]
            anim_index += 1
            
            status = (
                f"{COLOR_BOLD}{anim_char}{COLOR_RESET} "
                f"Progress: {COLOR_HIGHLIGHT}{progress:.1f}%{COLOR_RESET} "
                f"[{progress_bar}] "
                f"Pages: {COLOR_ACCENT}{self.page_count}{COLOR_RESET}/{self.max_pages} "
                f"| Assets: {COLOR_ACCENT}{self.asset_count}{COLOR_RESET} "
                f"| Depth: {COLOR_ACCENT}{depth}{COLOR_RESET}"
            )
            
            sys.stdout.write(f"\r{status}")
            sys.stdout.flush()
            
            # Process URL
            result = self.process_url(url, depth)
            if result:
                # Add found links to queue if we haven't reached max depth
                if depth < self.max_depth:
                    for link in result['links']:
                        if link not in self.visited:
                            self.to_visit.put((link, depth + 1))
                
                # Add to file tree
                self.file_tree[result['category']].append({
                    'url': url,
                    'path': result['path'],
                    'relative_path': result['relative_path'],
                    'size': os.path.getsize(result['path']) if os.path.exists(result['path']) else 0,
                    'type': result['type']
                })
        
        # Final report
        duration = time.time() - self.start_time
        terminal_width = shutil.get_terminal_size().columns
        
        self.log("\n\n" + "=" * terminal_width, "info")
        self.log("Scan completed successfully!", "success")
        self.log(f"Developer: {COLOR_HIGHLIGHT}Sabbona Tessema{COLOR_RESET}", "bold")
        self.log(f"Total pages processed: {COLOR_ACCENT}{self.page_count}{COLOR_RESET}", "info")
        self.log(f"Total assets downloaded: {COLOR_ACCENT}{self.asset_count}{COLOR_RESET}", "info")
        self.log(f"Errors encountered: {COLOR_WARNING if self.error_count > 0 else COLOR_SUCCESS}{self.error_count}{COLOR_RESET}", "info")
        self.log(f"Time taken: {COLOR_ACCENT}{duration:.2f} seconds{COLOR_RESET}", "info")
        self.log(f"Output saved to: {COLOR_ACCENT}{os.path.abspath(self.root_folder)}{COLOR_RESET}", "info")
        
        # Save file tree as JSON
        tree_path = os.path.join(self.root_folder, "sabbona_file_tree.json")
        with open(tree_path, 'w') as f:
            json.dump(self.file_tree, f, indent=2)
        self.log(f"File tree saved to: {COLOR_ACCENT}{tree_path}{COLOR_RESET}", "info")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print a visually appealing summary of downloaded files"""
        terminal_width = shutil.get_terminal_size().columns
        print("\n" + "=" * terminal_width)
        print(f"{COLOR_BOLD}{COLOR_HIGHLIGHT}SabbonaScan - Download Summary:{COLOR_RESET}")
        print("-" * terminal_width)
        print(f"{COLOR_BOLD}{'Category':<20} {'Files':<8} {'Size':<12} {'Avg Size':<12}{COLOR_RESET}")
        print("-" * terminal_width)
        
        total_size = 0
        for category, files in sorted(self.file_tree.items()):
            count = len(files)
            size = sum(f['size'] for f in files)
            avg_size = size / count if count > 0 else 0
            total_size += size
            
            # Apply color based on file type
            if category == 'html':
                color = COLOR_PRIMARY
            elif category == 'images':
                color = COLOR_SUCCESS
            elif category == 'js':
                color = COLOR_WARNING
            elif category == 'css':
                color = COLOR_ACCENT
            else:
                color = COLOR_RESET
                
            print(f"{color}{category.capitalize():<20}{COLOR_RESET} {count:<8} "
                  f"{self.format_size(size):<12} {self.format_size(avg_size):<12}")
        
        print("-" * terminal_width)
        print(f"{COLOR_BOLD}{'TOTAL':<20} {self.asset_count:<8} {self.format_size(total_size):<12}{COLOR_RESET}")
        print("=" * terminal_width)
        print(f"{COLOR_BOLD}Created by Sabbona Tessema - Comprehensive Website Scanning{COLOR_RESET}")
        print("=" * terminal_width)
    
    def stop(self):
        self.running = False
        self.log("Scan stopped by user", "warning", "STOPPED")
    
    @staticmethod
    def format_size(size):
        """Format file size in human-readable format with colors"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{COLOR_SUCCESS}{size/1024:.1f} KB{COLOR_RESET}"
        elif size < 1024 * 1024 * 1024:
            return f"{COLOR_WARNING}{size/(1024*1024):.1f} MB{COLOR_RESET}"
        else:
            return f"{COLOR_ERROR}{size/(1024*1024*1024):.1f} GB{COLOR_RESET}"
    
    def show_donation_info(self):
        """Display donation information in a visually appealing way"""
        terminal_width = shutil.get_terminal_size().columns
        print("\n" + "=" * terminal_width)
        print(f"{COLOR_BOLD}{COLOR_DONATE}Support SabbonaScan Development{COLOR_RESET}".center(terminal_width))
        print("-" * terminal_width)
        
        donation_message = [
            f"{COLOR_PRIMARY}If you find this tool valuable, consider supporting",
            f"its development and maintenance. Your contribution helps:",
            "",
            f"{COLOR_SUCCESS}✓ {COLOR_RESET}Add new features and improvements",
            f"{COLOR_SUCCESS}✓ {COLOR_RESET}Maintain server infrastructure",
            f"{COLOR_SUCCESS}✓ {COLOR_RESET}Support future open-source projects",
            "",
            f"{COLOR_BOLD}Donation Options:{COLOR_RESET}",
            "",
            f"{COLOR_ACCENT}1. GitHub Sponsors: {COLOR_HIGHLIGHT}https://github.com/sponsors/sabbona{COLOR_RESET}",
            f"{COLOR_ACCENT}2. PayPal: {COLOR_HIGHLIGHT}https://paypal.me/sabbonadev{COLOR_RESET}",
            f"{COLOR_ACCENT}3. Cryptocurrency:",
            f"   {COLOR_WARNING}• Bitcoin (BTC):{COLOR_RESET} bc1qexampleaddress",
            f"   {COLOR_WARNING}• Ethereum (ETH):{COLOR_RESET} 0xExampleEthereumAddress",
            "",
            f"{COLOR_SUPPORT}Your support is greatly appreciated!{COLOR_RESET}"
        ]
        
        for line in donation_message:
            print(line.center(terminal_width))
        
        print("=" * terminal_width)
        
        # Add QR code display option for crypto donations
        if platform.system() in ['Darwin', 'Linux', 'Windows']:
            choice = input(f"\n{COLOR_BOLD}Would you like to view QR codes for crypto donations? (y/n): {COLOR_RESET}").strip().lower()
            if choice == 'y':
                self.show_crypto_qr_codes()
    
    def show_crypto_qr_codes(self):
        """Display cryptocurrency donation QR codes in terminal"""
        try:
            import pyqrcode
        except ImportError:
            self.log("QR code display requires pyqrcode library", "warning")
            self.log("Install with: pip install pyqrcode", "info")
            return
        
        terminal_width = shutil.get_terminal_size().columns
        
        # Bitcoin QR
        btc_address = "bc1qexampleaddress"
        btc_qr = pyqrcode.create(btc_address)
        btc_qr.png("btc_donation.png", scale=6)
        
        # Ethereum QR
        eth_address = "0xExampleEthereumAddress"
        eth_qr = pyqrcode.create(eth_address)
        eth_qr.png("eth_donation.png", scale=6)
        
        print("\n" + "=" * terminal_width)
        print(f"{COLOR_BOLD}{COLOR_WARNING}Bitcoin Donation Address{COLOR_RESET}".center(terminal_width))
        print("-" * terminal_width)
        print(btc_address.center(terminal_width))
        print()
        
        # Display QR code using terminal capabilities
        try:
            if platform.system() == 'Windows':
                os.system(f"start btc_donation.png")
            elif platform.system() == 'Darwin':  # macOS
                os.system(f"open btc_donation.png")
            else:  # Linux
                os.system(f"xdg-open btc_donation.png")
        except:
            self.log("Couldn't open QR code image automatically", "warning")
            self.log("Open 'btc_donation.png' manually to view QR code", "info")
        
        print("\n" + "=" * terminal_width)
        print(f"{COLOR_BOLD}{COLOR_WARNING}Ethereum Donation Address{COLOR_RESET}".center(terminal_width))
        print("-" * terminal_width)
        print(eth_address.center(terminal_width))
        print()
        
        try:
            if platform.system() == 'Windows':
                os.system(f"start eth_donation.png")
            elif platform.system() == 'Darwin':  # macOS
                os.system(f"open eth_donation.png")
            else:  # Linux
                os.system(f"xdg-open eth_donation.png")
        except:
            self.log("Couldn't open QR code image automatically", "warning")
            self.log("Open 'eth_donation.png' manually to view QR code", "info")
        
        print("=" * terminal_width)
        print(f"{COLOR_SUCCESS}Thank you for your support!{COLOR_RESET}".center(terminal_width))
        print("=" * terminal_width)
        
        # Ask if user wants to keep the QR codes
        keep = input(f"\n{COLOR_BOLD}Keep QR code images? (y/n): {COLOR_RESET}").strip().lower()
        if keep != 'y':
            try:
                os.remove("btc_donation.png")
                os.remove("eth_donation.png")
            except:
                pass


def main():
    # Create scanner instance
    scanner = SabbonaScanner("", verbose=False)
    scanner.print_header()
    
    # Check for donation command first
    if len(sys.argv) > 1 and sys.argv[1] in ['--donate', 'give', 'support']:
        scanner.show_donation_info()
        sys.exit(0)
    
    # Get input from user
    if len(sys.argv) > 1:
        # Command-line mode
        url = sys.argv[1]
        depth = 5
        pages = 500
        output_dir = None
        verbose = False
        preserve_structure = True  # Default to preserving structure
        
        # Parse command-line options
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "-d" and i+1 < len(sys.argv):
                depth = int(sys.argv[i+1])
                i += 1
            elif sys.argv[i] == "-p" and i+1 < len(sys.argv):
                pages = int(sys.argv[i+1])
                i += 1
            elif sys.argv[i] == "-o" and i+1 < len(sys.argv):
                output_dir = sys.argv[i+1]
                i += 1
            elif sys.argv[i] == "-v":
                verbose = True
            elif sys.argv[i] == "--categorized":
                preserve_structure = False
            i += 1
        
        scanner = SabbonaScanner(
            base_url=url,
            output_dir=output_dir,
            max_depth=depth,
            max_pages=pages,
            verbose=verbose,
            preserve_structure=preserve_structure
        )
        scanner.crawl()
    else:
        # Interactive mode
        print(f"{COLOR_BOLD}Enter website URL to scan (e.g., example.com){COLOR_RESET}")
        print(f"{COLOR_ACCENT}Options:{COLOR_RESET}")
        print(f"  {COLOR_HIGHLIGHT}-d NUM{COLOR_RESET}   Set crawl depth (default: 5)")
        print(f"  {COLOR_HIGHLIGHT}-p NUM{COLOR_RESET}   Set max pages to scan (default: 500)")
        print(f"  {COLOR_HIGHLIGHT}-o DIR{COLOR_RESET}   Set output directory")
        print(f"  {COLOR_HIGHLIGHT}-v{COLOR_RESET}       Enable verbose output")
        print(f"  {COLOR_HIGHLIGHT}--categorized{COLOR_RESET} Use category folders instead of site structure")
        print(f"  {COLOR_DONATE}give{COLOR_RESET}       Show support options")
        print(f"{COLOR_WARNING}Type 'exit' to quit{COLOR_RESET}")
        
        while True:
            try:
                # Get user input
                command = input(f"\n{COLOR_BOLD}{COLOR_PRIMARY}SABBONA>{COLOR_RESET} ").strip()
                
                if command.lower() in ['exit', 'quit']:
                    print(f"{COLOR_SUCCESS}Exiting SabbonaScan. Goodbye!{COLOR_RESET}")
                    break
                    
                if command.lower() in ['give', 'donate', 'support']:
                    scanner.show_donation_info()
                    continue
                    
                if not command:
                    continue
                    
                # Parse command
                parts = command.split()
                url = None
                depth = 5
                pages = 500
                output_dir = None
                verbose = False
                preserve_structure = True
                
                # Parse options
                i = 0
                while i < len(parts):
                    part = parts[i]
                    if part.startswith("http://") or part.startswith("https://"):
                        url = part
                    elif part == "-d" and i+1 < len(parts):
                        depth = int(parts[i+1])
                        i += 1
                    elif part == "-p" and i+1 < len(parts):
                        pages = int(parts[i+1])
                        i += 1
                    elif part == "-o" and i+1 < len(parts):
                        output_dir = parts[i+1]
                        i += 1
                    elif part == "-v":
                        verbose = True
                    elif part == "--categorized":
                        preserve_structure = False
                    elif "://" not in part and url is None:
                        # Assume it's a URL without protocol
                        url = f"https://{part}"
                    i += 1
                    
                if url is None:
                    print(f"{COLOR_ERROR}Error: No website URL provided{COLOR_RESET}")
                    continue
                    
                # Run the scanner
                scanner = SabbonaScanner(
                    base_url=url,
                    output_dir=output_dir,
                    max_depth=depth,
                    max_pages=pages,
                    verbose=verbose,
                    preserve_structure=preserve_structure
                )
                
                # Start the scan in a separate thread
                scan_thread = threading.Thread(target=scanner.crawl)
                scan_thread.daemon = True
                scan_thread.start()
                
                # Wait for scan to complete or for keyboard interrupt
                try:
                    while scan_thread.is_alive():
                        scan_thread.join(0.1)
                except KeyboardInterrupt:
                    scanner.stop()
                    print(f"\n{COLOR_WARNING}Scan interrupted by user. Stopping...{COLOR_RESET}")
                    scan_thread.join()
                    
            except KeyboardInterrupt:
                print(f"\n{COLOR_WARNING}Operation cancelled by user.{COLOR_RESET}")
            except Exception as e:
                print(f"{COLOR_ERROR}Error: {str(e)}{COLOR_RESET}")


if __name__ == "__main__":
    main()
