#!/usr/bin/env python3
"""
Documentation Fetch Script for Claude Code
Fetches and processes documentation from various sources into AI-friendly Markdown format.
"""

import argparse
import os
import sys
import time
import subprocess
from urllib.parse import urljoin, urlparse
from pathlib import Path
import json
import re
from typing import Dict, List, Optional, Tuple
import logging
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentQualityValidator:
    """Validates content quality and completeness."""
    
    def __init__(self):
        self.quality_thresholds = {
            'min_content_length': 500,
            'min_headings': 2,
            'min_code_blocks': 0,
            'max_js_indicators': 3
        }
    
    def validate_content_quality(self, content: str, url: str) -> Dict:
        """Validate content quality and return metrics."""
        if not content:
            return {
                'is_valid': False,
                'completeness': 0,
                'issues': ['No content'],
                'metrics': {}
            }
        
        metrics = self._calculate_content_metrics(content)
        issues = self._identify_content_issues(content, metrics)
        completeness = self._calculate_completeness(metrics, issues)
        
        return {
            'is_valid': completeness >= 50,
            'completeness': completeness,
            'issues': issues,
            'metrics': metrics,
            'url': url
        }
    
    def _calculate_content_metrics(self, content: str) -> Dict:
        """Calculate various content quality metrics."""
        content_lower = content.lower()
        
        metrics = {
            'length': len(content),
            'headings': len(re.findall(r'<h[1-6][^>]*>', content, re.IGNORECASE)),
            'code_blocks': len(re.findall(r'<pre[^>]*>|<code[^>]*>', content, re.IGNORECASE)),
            'links': len(re.findall(r'<a[^>]*href', content, re.IGNORECASE)),
            'paragraphs': len(re.findall(r'<p[^>]*>', content, re.IGNORECASE)),
            'documentation_keywords': 0,
            'js_loading_indicators': 0
        }
        
        # Count documentation keywords
        doc_keywords = [
            'api', 'documentation', 'guide', 'tutorial', 'reference',
            'function', 'method', 'class', 'parameter', 'example',
            'usage', 'install', 'configuration'
        ]
        
        for keyword in doc_keywords:
            if keyword in content_lower:
                metrics['documentation_keywords'] += content_lower.count(keyword)
        
        # Count JS loading indicators (bad signs)
        js_indicators = [
            'loading...', 'please wait', 'javascript required',
            'enable javascript', 'noscript', 'document.getelementbyid'
        ]
        
        for indicator in js_indicators:
            if indicator in content_lower:
                metrics['js_loading_indicators'] += content_lower.count(indicator)
        
        return metrics
    
    def _identify_content_issues(self, content: str, metrics: Dict) -> List[str]:
        """Identify content quality issues."""
        issues = []
        
        if metrics['length'] < self.quality_thresholds['min_content_length']:
            issues.append(f"Content too short ({metrics['length']} chars)")
        
        if metrics['headings'] < self.quality_thresholds['min_headings']:
            issues.append(f"Too few headings ({metrics['headings']})")
        
        if metrics['js_loading_indicators'] > self.quality_thresholds['max_js_indicators']:
            issues.append("Too many JavaScript loading indicators")
        
        if metrics['documentation_keywords'] == 0:
            issues.append("No documentation keywords found")
        
        # Check for empty or mostly empty content
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        if len(text_content) < 200:
            issues.append("Very little actual text content")
        
        return issues
    
    def _calculate_completeness(self, metrics: Dict, issues: List[str]) -> int:
        """Calculate content completeness percentage."""
        score = 100
        
        # Deduct points for each issue
        score -= len(issues) * 15
        
        # Bonus for good indicators
        if metrics['documentation_keywords'] > 5:
            score += 10
        
        if metrics['code_blocks'] > 0:
            score += 10
        
        if metrics['headings'] > 5:
            score += 10
        
        # Cap at 0-100 range
        return max(0, min(100, score))

class DocsFetcher:
    """Main class for fetching and processing documentation."""
    
    def __init__(self, base_dir: str = "/workspace/docs"):
        self.base_dir = Path(base_dir)
        self.user_agent = 'Mozilla/5.0 (compatible; Claude-Code-DocsFetch/1.0; +https://claude.ai/code)'
        
        # Rate limiting configuration
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0.0
        
        # Error handling and retry configuration
        self.max_retries = 3
        self.retry_delays = [1, 3, 8]  # Exponential backoff in seconds
        self.timeout_seconds = 90
        
        # Site patterns for common documentation sites
        self.site_patterns = self._load_site_patterns()
        
        # Content quality validation
        self.quality_validator = ContentQualityValidator()
        
        # Enhanced headers for better compatibility
        self.enhanced_headers = [
            '-H', f'User-Agent: {self.user_agent}',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', 'Accept-Encoding: gzip, deflate, br',
            '-H', 'Connection: keep-alive',
            '-H', 'Upgrade-Insecure-Requests: 1'
        ]
        
        # JS-heavy sites that need special handling
        self.js_heavy_sites = {
            'react.dev', 'vuejs.org', 'angular.dev', 'nextjs.org',
            'docs.svelte.dev', 'tailwindcss.com'
        }
    
    def _load_site_patterns(self) -> Dict:
        """Load site-specific parsing patterns from user-writable storage."""
        # Create user-writable patterns directory
        user_patterns_dir = self.base_dir / '.site-patterns'
        user_patterns_dir.mkdir(parents=True, exist_ok=True)
        
        patterns = {}
        
        # Load built-in patterns first (fallback)
        builtin_patterns = self._get_builtin_patterns()
        patterns.update(builtin_patterns)
        
        # Load user patterns (override built-in ones)
        for pattern_file in user_patterns_dir.glob('*.json'):
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    domain = pattern_file.stem  # filename without .json
                    user_pattern = json.load(f)
                    
                    # Validate and update pattern
                    if self._validate_pattern(user_pattern):
                        patterns[domain] = user_pattern
                        logger.info(f"Loaded user pattern for {domain}")
                    else:
                        logger.warning(f"Invalid user pattern in {pattern_file}, skipping")
                        
            except Exception as e:
                logger.error(f"Error loading pattern from {pattern_file}: {str(e)}")
        
        return patterns
    
    def _get_builtin_patterns(self) -> Dict:
        """Get built-in fallback patterns."""
        # Try to load from the static file first
        patterns_file = Path(__file__).parent / "site-patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Fallback to hardcoded patterns
        return {
            "react.dev": {
                "selectors": {
                    "main_content": "main[role='main']",
                    "navigation": "nav[role='navigation']", 
                    "title": "h1"
                },
                "base_urls": ["https://react.dev/"],
                "sections": ["learn", "reference", "community"],
                "metadata": {
                    "success_rate": 0.85,
                    "last_updated": "2025-01-01",
                    "usage_count": 0
                }
            },
            "docs.python.org": {
                "selectors": {
                    "main_content": ".body-content",
                    "navigation": ".toctree-wrapper",
                    "title": "h1"
                },
                "base_urls": ["https://docs.python.org/3/"],
                "sections": ["tutorial", "library", "reference"],
                "metadata": {
                    "success_rate": 0.90,
                    "last_updated": "2025-01-01", 
                    "usage_count": 0
                }
            },
            "default": {
                "selectors": {
                    "main_content": "main, .main, .content, .container, article, .document",
                    "navigation": "nav, .nav, .sidebar, .toc",
                    "title": "h1, .title, .page-title"
                },
                "sections": ["docs", "guide", "api", "reference"],
                "metadata": {
                    "success_rate": 0.70,
                    "last_updated": "2025-01-01",
                    "usage_count": 0
                }
            }
        }
    
    def _validate_pattern(self, pattern: Dict) -> bool:
        """Validate a site pattern structure."""
        required_keys = ['selectors']
        if not all(key in pattern for key in required_keys):
            return False
        
        # Validate selectors
        selectors = pattern.get('selectors', {})
        if not isinstance(selectors, dict) or not selectors:
            return False
        
        return True
    
    def _save_learned_pattern(self, domain: str, pattern: Dict):
        """Save a learned pattern to user-writable storage."""
        try:
            user_patterns_dir = self.base_dir / '.site-patterns'
            user_patterns_dir.mkdir(parents=True, exist_ok=True)
            
            pattern_file = user_patterns_dir / f"{domain}.json"
            
            with open(pattern_file, 'w', encoding='utf-8') as f:
                json.dump(pattern, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved learned pattern for {domain}")
            
        except Exception as e:
            logger.error(f"Error saving pattern for {domain}: {str(e)}")
    
    def _discover_content_patterns(self, html_content: str, url: str) -> Dict:
        """Analyze HTML to discover content patterns."""
        from urllib.parse import urlparse
        
        if not html_content:
            return {}
        
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Analyze common content indicators
        selectors = {
            "main_content": [],
            "navigation": [], 
            "title": []
        }
        
        # Look for main content indicators
        main_indicators = [
            ('main[role="main"]', html_content.count('main role="main"')),
            ('main', html_content.count('<main')),
            ('.main-content', html_content.count('class="main-content"') + html_content.count("class='main-content'")),
            ('.content', html_content.count('class="content"') + html_content.count("class='content'")),
            ('article', html_content.count('<article')),
            ('.container', html_content.count('class="container"') + html_content.count("class='container'")),
            ('.docs-content', html_content.count('docs-content'))
        ]
        
        # Sort by frequency and pick the most common ones
        main_indicators.sort(key=lambda x: x[1], reverse=True)
        selectors["main_content"] = [sel[0] for sel in main_indicators[:3] if sel[1] > 0]
        
        # Look for navigation indicators
        nav_indicators = [
            ('nav', html_content.count('<nav')),
            ('.nav', html_content.count('class="nav"') + html_content.count("class='nav'")),
            ('.sidebar', html_content.count('sidebar')),
            ('.toc', html_content.count('toc')),
            ('.navigation', html_content.count('navigation'))
        ]
        
        nav_indicators.sort(key=lambda x: x[1], reverse=True)
        selectors["navigation"] = [sel[0] for sel in nav_indicators[:2] if sel[1] > 0]
        
        # Title indicators
        selectors["title"] = ["h1", ".title", ".page-title"]
        
        # Create pattern
        pattern = {
            "selectors": {
                "main_content": ", ".join(selectors["main_content"]) or "main, .content, article",
                "navigation": ", ".join(selectors["navigation"]) or "nav, .sidebar", 
                "title": ", ".join(selectors["title"])
            },
            "base_urls": [f"https://{domain}/"],
            "metadata": {
                "success_rate": 0.5,  # Initial success rate
                "last_updated": time.strftime('%Y-%m-%d'),
                "usage_count": 1,
                "discovered": True
            }
        }
        
        return pattern
    
    def _update_pattern_success(self, domain: str, success: bool):
        """Update pattern success metrics."""
        try:
            user_patterns_dir = self.base_dir / '.site-patterns'
            pattern_file = user_patterns_dir / f"{domain}.json"
            
            if pattern_file.exists():
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern = json.load(f)
                
                metadata = pattern.get('metadata', {})
                
                # Update usage count
                metadata['usage_count'] = metadata.get('usage_count', 0) + 1
                
                # Update success rate using exponential moving average
                current_rate = metadata.get('success_rate', 0.5)
                alpha = 0.1  # Learning rate
                new_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_rate
                metadata['success_rate'] = round(new_rate, 3)
                metadata['last_updated'] = time.strftime('%Y-%m-%d')
                
                pattern['metadata'] = metadata
                
                # Save updated pattern
                with open(pattern_file, 'w', encoding='utf-8') as f:
                    json.dump(pattern, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Updated pattern success for {domain}: rate={new_rate:.3f}, count={metadata['usage_count']}")
                
        except Exception as e:
            logger.error(f"Error updating pattern success for {domain}: {str(e)}")
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem storage."""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        return filename.strip('._')
    
    def _determine_library_type(self, library_name: str) -> str:
        """Determine if library is a framework, language, or library."""
        frameworks = {'react', 'vue', 'angular', 'nextjs', 'nuxt', 'svelte', 'express', 'fastapi', 'django', 'flask'}
        languages = {'python', 'javascript', 'typescript', 'rust', 'go', 'java', 'cpp', 'c', 'php'}
        
        library_lower = library_name.lower()
        
        if library_lower in frameworks:
            return 'frameworks'
        elif library_lower in languages:
            return 'languages'
        else:
            return 'libraries'
    
    def _create_directory_structure(self, library_name: str) -> Path:
        """Create appropriate directory structure for the library."""
        library_type = self._determine_library_type(library_name)
        lib_dir = self.base_dir / library_type / library_name.lower()
        lib_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (lib_dir / 'examples').mkdir(exist_ok=True)
        
        return lib_dir
    
    def _discover_documentation_urls(self, library_name: str) -> List[str]:
        """Discover official documentation URLs for a given library."""
        logger.info(f"Discovering documentation URLs for: {library_name}")
        
        # Special cases for well-known libraries (most reliable)
        special_cases = {
            'react': ['https://react.dev/', 'https://reactjs.org/docs/'],
            'vue': ['https://vuejs.org/guide/', 'https://v2.vuejs.org/v2/guide/'],
            'angular': ['https://angular.dev/', 'https://angular.io/docs'],
            'python': ['https://docs.python.org/3/'],
            'javascript': ['https://developer.mozilla.org/en-US/docs/Web/JavaScript'],
            'typescript': ['https://www.typescriptlang.org/docs/'],
            'lodash': ['https://lodash.com/docs/', 'https://github.com/lodash/lodash/tree/main/docs'],
            'express': ['https://expressjs.com/', 'https://expressjs.com/en/4x/api.html'],
            'nextjs': ['https://nextjs.org/docs'],
            'svelte': ['https://svelte.dev/docs'],
            'tailwindcss': ['https://tailwindcss.com/docs'],
            'bootstrap': ['https://getbootstrap.com/docs/'],
            'jquery': ['https://api.jquery.com/', 'https://jquery.com/'],
            'webpack': ['https://webpack.js.org/concepts/'],
            'vite': ['https://vitejs.dev/guide/'],
            'eslint': ['https://eslint.org/docs/'],
            'prettier': ['https://prettier.io/docs/'],
            'jest': ['https://jestjs.io/docs/'],
            'cypress': ['https://docs.cypress.io/'],
            'storybook': ['https://storybook.js.org/docs/'],
            'material-ui': ['https://mui.com/getting-started/'],
            'antd': ['https://ant.design/components/overview/'],
            'chakra-ui': ['https://chakra-ui.com/docs/'],
            'redis': ['https://redis.io/documentation'],
            'mongodb': ['https://docs.mongodb.com/'],
            'postgresql': ['https://www.postgresql.org/docs/'],
            'mysql': ['https://dev.mysql.com/doc/'],
            'django': ['https://docs.djangoproject.com/'],
            'flask': ['https://flask.palletsprojects.com/'],
            'fastapi': ['https://fastapi.tiangolo.com/'],
            'rails': ['https://guides.rubyonrails.org/'],
            'laravel': ['https://laravel.com/docs'],
            'spring': ['https://docs.spring.io/spring-framework/docs/current/reference/html/'],
            'numpy': ['https://numpy.org/doc/stable/'],
            'pandas': ['https://pandas.pydata.org/docs/'],
            'tensorflow': ['https://www.tensorflow.org/guide'],
            'pytorch': ['https://pytorch.org/docs/stable/'],
            'rust': ['https://doc.rust-lang.org/book/'],
            'go': ['https://golang.org/doc/', 'https://pkg.go.dev/std'],
            'java': ['https://docs.oracle.com/javase/tutorial/'],
            'kotlin': ['https://kotlinlang.org/docs/'],
            'swift': ['https://docs.swift.org/swift-book/'],
            'dart': ['https://dart.dev/guides'],
            'flutter': ['https://docs.flutter.dev/'],
        }
        
        if library_name.lower() in special_cases:
            logger.info(f"Using known URLs for {library_name}")
            return special_cases[library_name.lower()]
        
        # Extended URL patterns for discovery
        lib_lower = library_name.lower()
        common_patterns = [
            # Primary documentation sites
            f"https://{lib_lower}.dev/",
            f"https://docs.{lib_lower}.org/",
            f"https://{lib_lower}.org/docs/",
            f"https://{lib_lower}.org/documentation/",
            f"https://{lib_lower}.readthedocs.io/",
            f"https://{lib_lower}.readthedocs.io/en/latest/",
            f"https://readthedocs.org/projects/{lib_lower}/",
            
            # Alternative patterns
            f"https://www.{lib_lower}.org/docs/",
            f"https://www.{lib_lower}.com/docs/",
            f"https://{lib_lower}.com/docs/",
            f"https://{lib_lower}.io/docs/",
            f"https://docs.{lib_lower}.io/",
            f"https://guide.{lib_lower}.org/",
            f"https://api.{lib_lower}.org/",
            
            # GitHub documentation
            f"https://github.com/{lib_lower}/{lib_lower}/tree/main/docs",
            f"https://github.com/{lib_lower}/{lib_lower}/wiki",
            f"https://{lib_lower}.github.io/",
            f"https://{lib_lower}.github.io/docs/",
            
            # NPM package docs
            f"https://www.npmjs.com/package/{lib_lower}",
            
            # Python package docs
            f"https://pypi.org/project/{lib_lower}/",
            f"https://{lib_lower}.pypa.io/",
            
            # Language-specific patterns
            f"https://pkg.go.dev/{lib_lower}",
            f"https://crates.io/crates/{lib_lower}",
            f"https://packagist.org/packages/{lib_lower}",
        ]
        
        logger.info(f"Testing {len(common_patterns)} URL patterns...")
        working_urls = []
        
        for i, url in enumerate(common_patterns):
            try:
                self._enforce_rate_limit()
                logger.debug(f"Testing URL {i+1}/{len(common_patterns)}: {url}")
                
                # Use curl to test URL accessibility
                result = subprocess.run([
                    'curl', '-s', '-I', '--connect-timeout', '8', '--max-time', '15',
                    '-H', f'User-Agent: {self.user_agent}', url
                ], capture_output=True, text=True, timeout=20)
                
                if result.returncode == 0 and result.stdout:
                    # Check for successful HTTP responses
                    if any(status in result.stdout for status in ['200 OK', '301 ', '302 ', '303 ']):
                        working_urls.append(url)
                        logger.info(f"✅ Found working URL: {url}")
                        if len(working_urls) >= 3:  # Limit to first 3 working URLs
                            break
                            
            except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
                logger.debug(f"Failed to test {url}: {str(e)}")
                continue
        
        if working_urls:
            logger.info(f"Discovered {len(working_urls)} working URLs for {library_name}")
        else:
            logger.warning(f"No working URLs found for {library_name} after testing {len(common_patterns)} patterns")
        
        return working_urls
    
    def _requires_enhanced_fetching(self, url: str) -> bool:
        """Check if URL requires enhanced fetching strategies."""
        from urllib.parse import urlparse
        
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return any(js_site in domain for js_site in self.js_heavy_sites)
    
    def _fetch_with_retry(self, url: str, use_enhanced_headers: bool = True) -> Optional[str]:
        """Fetch URL with retry logic and exponential backoff."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                    logger.info(f"Waiting {delay}s before retry attempt {attempt + 1}")
                    time.sleep(delay)
                
                logger.info(f"Fetch attempt {attempt + 1}/{self.max_retries} for: {url}")
                
                # Build curl command
                cmd = ['curl', '-s', '-L', '--connect-timeout', '30', '--max-time', '60']
                
                if use_enhanced_headers:
                    cmd.extend(self.enhanced_headers)
                    cmd.append('--compressed')
                else:
                    cmd.extend(['-H', f'User-Agent: {self.user_agent}'])
                
                cmd.append(url)
                
                # Execute the request
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_seconds)
                
                if result.returncode == 0 and result.stdout.strip():
                    content = result.stdout
                    
                    # Validate content quality
                    quality = self.quality_validator.validate_content_quality(content, url)
                    
                    if quality['is_valid'] or attempt == self.max_retries - 1:
                        if quality['is_valid']:
                            logger.info(f"Fetch successful (quality: {quality['completeness']}%)")
                        else:
                            logger.warning(f"Using low-quality content after all retries (issues: {quality['issues']})")
                        return content
                    else:
                        logger.warning(f"Content quality too low (attempt {attempt + 1}): {quality['issues']}")
                        continue
                        
                else:
                    last_error = f"curl failed with return code {result.returncode}: {result.stderr}"
                    logger.warning(f"Attempt {attempt + 1} failed: {last_error}")
                    
            except subprocess.TimeoutExpired:
                last_error = f"Request timed out after {self.timeout_seconds} seconds"
                logger.warning(f"Attempt {attempt + 1} timed out")
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Attempt {attempt + 1} failed with error: {last_error}")
        
        logger.error(f"All {self.max_retries} attempts failed for {url}. Last error: {last_error}")
        return None
    
    def _enhanced_fetch(self, url: str) -> Optional[str]:
        """Enhanced fetch with better headers and retry logic."""
        # Try with enhanced headers first
        content = self._fetch_with_retry(url, use_enhanced_headers=True)
        
        if content:
            return content
        
        # Fallback to simple headers
        logger.info("Enhanced headers failed, trying with simple headers")
        return self._fetch_with_retry(url, use_enhanced_headers=False)
    
    def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch content from a single URL with comprehensive error handling."""
        try:
            self._enforce_rate_limit()
            logger.info(f"Fetching content from: {url}")
            
            # Use enhanced fetching for all sites (includes retry logic)
            if self._requires_enhanced_fetching(url):
                logger.info(f"Using enhanced fetching for JS-heavy site: {url}")
                return self._enhanced_fetch(url)
            else:
                logger.info(f"Using standard fetching with retry logic: {url}")
                return self._fetch_with_retry(url, use_enhanced_headers=False)
        
        except Exception as e:
            logger.error(f"Critical error fetching {url}: {str(e)}")
            return None
    
    def parse_arguments(self, args_string: str) -> Tuple[str, Dict]:
        """Parse command line arguments from string."""
        # Split the arguments string into components
        args = args_string.strip().split()
        
        if not args:
            raise ValueError("No library name provided")
        
        library_name = args[0]
        options = {}
        
        # Parse optional flags
        i = 1
        while i < len(args):
            if args[i].startswith('--'):
                flag = args[i][2:]  # Remove '--'
                if i + 1 < len(args) and not args[i + 1].startswith('--'):
                    options[flag] = args[i + 1]
                    i += 2
                else:
                    options[flag] = True
                    i += 1
            else:
                i += 1
        
        return library_name, options
    
    def _process_content_with_markdown_converter(self, html_content: str, base_url: str) -> str:
        """Process HTML content using the markdown converter."""
        try:
            # Load and use the markdown converter
            converter_path = Path(__file__).parent / "markdown-converter.py"
            if not converter_path.exists():
                logger.warning("Markdown converter not found, using basic HTML stripping")
                return re.sub(r'<[^>]+>', ' ', html_content)
            
            # Create a temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
                html_file.write(html_content)
                html_path = html_file.name
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as md_file:
                md_path = md_file.name
            
            # Call the markdown converter
            result = subprocess.run([
                sys.executable, str(converter_path), html_path, md_path, base_url
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                with open(md_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                return markdown_content
            else:
                logger.error(f"Markdown converter failed: {result.stderr}")
                return re.sub(r'<[^>]+>', ' ', html_content)
                
        except Exception as e:
            logger.error(f"Error in markdown conversion: {str(e)}")
            return re.sub(r'<[^>]+>', ' ', html_content)
        finally:
            # Clean up temporary files
            try:
                if 'html_path' in locals():
                    os.unlink(html_path)
                if 'md_path' in locals():
                    os.unlink(md_path)
            except:
                pass
    
    def create_metadata(self, library_name: str, urls: List[str], version: str = None) -> Dict:
        """Create metadata for the documentation."""
        return {
            'library': library_name,
            'version': version or 'latest',
            'source_urls': urls,
            'last_fetched': time.strftime('%Y-%m-%d'),
            'completeness': 0,  # Will be updated after processing
            'ai_optimized': True
        }
    
    def fetch_documentation(self, library_name: str, **options) -> bool:
        """Main method to fetch documentation for a library."""
        try:
            logger.info(f"Starting documentation fetch for: {library_name}")
            
            # Create directory structure
            lib_dir = self._create_directory_structure(library_name)
            
            # Check if user provided manual URL
            if 'url' in options:
                urls = [options['url']]
                logger.info(f"Using manually provided URL: {options['url']}")
            else:
                # Discover documentation URLs
                urls = self._discover_documentation_urls(library_name)
            
            if not urls:
                logger.error(f"❌ Could not find documentation URLs for '{library_name}'")
                print(f"\n❌ Documentation Discovery Failed")
                print(f"Could not automatically discover documentation URLs for '{library_name}'.")
                print(f"")
                print(f"This could happen because:")
                print(f"• The library name might be spelled incorrectly")
                print(f"• The library might not have online documentation")
                print(f"• The documentation might be at a non-standard URL")
                print(f"• Network connectivity issues")
                print(f"")
                print(f"Please provide the documentation URL manually:")
                print(f"Example: /docs:fetch {library_name} --url https://example.com/docs/")
                print(f"")
                print(f"Or check if you meant one of these popular libraries:")
                
                # Suggest similar library names
                similar_libs = self._suggest_similar_libraries(library_name)
                if similar_libs:
                    print(f"• " + "\n• ".join(similar_libs))
                
                return False
            
            # Create metadata
            metadata = self.create_metadata(library_name, urls, options.get('version'))
            
            # Fetch and process content from each URL
            processed_content = {}
            for i, url in enumerate(urls[:3]):  # Limit to first 3 URLs for now
                logger.info(f"Processing URL {i+1}/{min(len(urls), 3)}: {url}")
                
                # Fetch the content
                html_content = self.fetch_page_content(url)
                if not html_content:
                    self._update_pattern_success(self._get_domain(url), False)
                    continue
                
                # Validate content quality
                quality = self.quality_validator.validate_content_quality(html_content, url)
                
                # Learn from successful fetches
                if quality['is_valid']:
                    domain = self._get_domain(url)
                    if domain not in self.site_patterns:
                        # Discover and save new pattern
                        learned_pattern = self._discover_content_patterns(html_content, url)
                        if learned_pattern:
                            self._save_learned_pattern(domain, learned_pattern)
                            self.site_patterns[domain] = learned_pattern
                    
                    self._update_pattern_success(domain, True)
                else:
                    self._update_pattern_success(self._get_domain(url), False)
                
                # Convert HTML to Markdown
                markdown_content = self._process_content_with_markdown_converter(html_content, url)
                
                # Keep content processing deterministic and local; Claude has no
                # repository-owned subagent post-processing path.
                if markdown_content:
                    processed_content[url] = markdown_content
            
            # Check if we actually got any useful content
            if not processed_content:
                logger.error(f"❌ Failed to fetch any documentation content for '{library_name}'")
                print(f"\n❌ Content Fetch Failed")
                print(f"Found documentation URLs for '{library_name}' but failed to fetch content from all of them.")
                print(f"This could be due to:")
                print(f"• Network connectivity issues")
                print(f"• Website blocking automated requests")
                print(f"• Temporary server issues")
                print(f"• URLs requiring authentication")
                print(f"")
                print(f"Found URLs attempted:")
                for url in urls:
                    print(f"• {url}")
                print(f"")
                print(f"Please try again later, or provide a different URL:")
                print(f"Example: /docs:fetch {library_name} --url https://alternative-docs-url.com/")
                
                # Clean up empty directory structure
                import shutil
                try:
                    if lib_dir.exists():
                        shutil.rmtree(lib_dir)
                        logger.info(f"Cleaned up empty directory: {lib_dir}")
                except:
                    pass
                
                return False
            
            # Create documentation files
            self._create_documentation_files(lib_dir, library_name, metadata, urls, processed_content)
            
            # Update CLAUDE.md to reference the new documentation
            self._update_claude_md(library_name, lib_dir, metadata)
            
            logger.info(f"Documentation created for {library_name} in {lib_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {library_name}: {str(e)}")
            return False
    
    def _create_documentation_files(self, lib_dir: Path, library_name: str, metadata: Dict, urls: List[str], processed_content: Dict[str, str]):
        """Create documentation files from processed content."""
        # Update metadata completeness based on successful content processing
        completeness = int((len(processed_content) / len(urls)) * 100)
        metadata['completeness'] = completeness
        
        # Create index file
        index_content = f"""---
library: "{metadata['library']}"
version: "{metadata['version']}"
source_urls:
{chr(10).join(f'  - "{url}"' for url in metadata['source_urls'])}
last_fetched: "{metadata['last_fetched']}"
completeness: {metadata['completeness']}
ai_optimized: {metadata['ai_optimized']}
---

# {library_name.title()} Documentation

## Overview

This directory contains AI-optimized documentation for {library_name}, fetched from official sources and converted to Markdown format for enhanced Claude Code integration.

## Source URLs

The following official documentation sources were processed:

{chr(10).join(f'- [{url}]({url}) {"✅" if url in processed_content else "❌"}' for url in urls)}

## Structure

- `index.md` - This overview file
- `api-reference.md` - Complete API documentation
- `best-practices.md` - Current patterns and conventions  
- `examples/` - Practical implementation examples

## Content Status

- ✅ Directory structure created
- ✅ Source URLs identified  
- ✅ Content fetched ({len(processed_content)}/{len(urls)} sources)
- ✅ Content processed and AI-optimized
- ✅ Deterministic local Markdown processing

**Completeness: {completeness}%**

*Last updated: {metadata['last_fetched']}*
"""
        
        index_file = lib_dir / 'index.md'
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        logger.info(f"Created index file: {index_file}")
        
        # Create consolidated API reference from all processed content
        if processed_content:
            api_content = f"""---
library: "{metadata['library']}"
version: "{metadata['version']}"
last_fetched: "{metadata['last_fetched']}"
---

# {library_name.title()} API Reference

This document contains comprehensive API documentation for {library_name}, consolidated from official sources and optimized for AI assistance.

"""
            
            for i, (url, content) in enumerate(processed_content.items(), 1):
                api_content += f"\n## Source {i}: {url}\n\n"
                api_content += content
                api_content += "\n\n---\n\n"
            
            api_file = lib_dir / 'api-reference.md'
            with open(api_file, 'w', encoding='utf-8') as f:
                f.write(api_content)
            logger.info(f"Created API reference file: {api_file}")
        
        # Create best practices file template
        best_practices_content = f"""---
library: "{metadata['library']}"
version: "{metadata['version']}"
last_fetched: "{metadata['last_fetched']}"
---

# {library_name.title()} Best Practices

This document contains current patterns, conventions, and best practices for using {library_name}.

## Installation

*Installation instructions will be extracted from processed documentation*

## Getting Started

*Getting started guide will be populated from processed content*

## Common Patterns

*Common usage patterns will be identified and documented*

## Performance Considerations

*Performance tips and optimization strategies*

## Migration Guide

*Version migration information when available*

## Additional Resources

{chr(10).join(f'- [{url}]({url})' for url in urls)}
"""
        
        best_practices_file = lib_dir / 'best-practices.md'
        with open(best_practices_file, 'w', encoding='utf-8') as f:
            f.write(best_practices_content)
        logger.info(f"Created best practices file: {best_practices_file}")
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def _suggest_similar_libraries(self, library_name: str) -> List[str]:
        """Suggest similar library names based on common patterns."""
        # Get list of known libraries from special cases
        known_libraries = [
            'react', 'vue', 'angular', 'python', 'javascript', 'typescript',
            'lodash', 'express', 'nextjs', 'svelte', 'tailwindcss', 'bootstrap',
            'jquery', 'webpack', 'vite', 'eslint', 'prettier', 'jest', 'cypress',
            'storybook', 'material-ui', 'antd', 'chakra-ui', 'redis', 'mongodb',
            'postgresql', 'mysql', 'django', 'flask', 'fastapi', 'rails', 'laravel',
            'spring', 'numpy', 'pandas', 'tensorflow', 'pytorch', 'rust', 'go',
            'java', 'kotlin', 'swift', 'dart', 'flutter'
        ]
        
        library_lower = library_name.lower()
        suggestions = []
        
        # Find libraries with similar names
        for lib in known_libraries:
            # Exact substring match
            if library_lower in lib or lib in library_lower:
                suggestions.append(lib)
            # Similar starting letters
            elif len(library_lower) >= 3 and len(lib) >= 3:
                if library_lower[:3] == lib[:3] and len(suggestions) < 5:
                    suggestions.append(lib)
        
        # Add some common alternatives for popular misspellings
        alternatives = {
            'reactjs': ['react'],
            'vuejs': ['vue'],
            'angularjs': ['angular'],
            'nodejs': ['javascript', 'express'],
            'node': ['javascript', 'express'],
            'js': ['javascript'],
            'ts': ['typescript'],
            'py': ['python'],
            'tf': ['tensorflow'],
            'torch': ['pytorch'],
            'pg': ['postgresql'],
            'postgres': ['postgresql'],
            'mongo': ['mongodb'],
            'css': ['bootstrap', 'tailwindcss'],
            'mui': ['material-ui'],
            'ant': ['antd'],
            'chakra': ['chakra-ui']
        }
        
        if library_lower in alternatives:
            suggestions.extend(alternatives[library_lower])
        
        return list(set(suggestions))[:5]  # Return top 5 unique suggestions
    
    def _update_claude_md(self, library_name: str, lib_dir: Path, metadata: Dict):
        """Update CLAUDE.md to reference the newly fetched documentation."""
        try:
            claude_md_path = Path('/workspace/CLAUDE.md')
            if not claude_md_path.exists():
                logger.warning("CLAUDE.md not found, skipping documentation reference update")
                return
            
            with open(claude_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Determine library category
            library_type = self._determine_library_type(library_name)
            relative_path = f"docs/{library_type}/{library_name.lower()}"
            
            # Create documentation reference section if it doesn't exist
            docs_section = "\n## Available Documentation\n\nFetched documentation available for enhanced Claude Code assistance:\n\n"
            
            if "## Available Documentation" not in content:
                # Add the section before the "Important Workflow Patterns" section
                if "## Important Workflow Patterns" in content:
                    content = content.replace("## Important Workflow Patterns", docs_section + "## Important Workflow Patterns")
                else:
                    # Add at the end
                    content += docs_section
            
            # Create the documentation entry
            type_singular = library_type[:-1] if library_type.endswith('s') else library_type
            doc_entry = f"- **{library_name.title()}** ({type_singular}): `{relative_path}/` - {metadata.get('completeness', 0)}% complete"
            if metadata.get('version', 'latest') != 'latest':
                doc_entry += f" (v{metadata['version']})"
            doc_entry += f" - *Updated {metadata['last_fetched']}*\n"
            
            # Check if this library is already documented
            library_pattern = f"- **{library_name.title()}**"
            if library_pattern in content:
                # Update existing entry
                import re
                pattern = rf"- \*\*{re.escape(library_name.title())}\*\*.*?\n"
                content = re.sub(pattern, doc_entry, content)
                logger.info(f"Updated existing {library_name} reference in CLAUDE.md")
            else:
                # Add new entry
                docs_section_start = content.find("## Available Documentation")
                if docs_section_start != -1:
                    # Find the end of the section header and add the entry
                    section_end = content.find("\n\n", docs_section_start + len("## Available Documentation"))
                    if section_end != -1:
                        content = content[:section_end] + "\n" + doc_entry + content[section_end:]
                    else:
                        content += "\n" + doc_entry
                else:
                    content += doc_entry
                logger.info(f"Added new {library_name} reference to CLAUDE.md")
            
            # Write the updated content
            with open(claude_md_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            logger.error(f"Error updating CLAUDE.md: {str(e)}")
            # Don't fail the entire operation if CLAUDE.md update fails

def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python docs-fetch.py <library_name> [options]")
        print("Example: python docs-fetch.py react --version 18.3.0")
        sys.exit(1)
    
    # Parse arguments
    args_string = ' '.join(sys.argv[1:])
    fetcher = DocsFetcher()
    
    try:
        library_name, options = fetcher.parse_arguments(args_string)
        success = fetcher.fetch_documentation(library_name, **options)
        
        if success:
            print(f"✅ Documentation structure created for {library_name}")
            sys.exit(0)
        else:
            print(f"❌ Failed to fetch documentation for {library_name}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()