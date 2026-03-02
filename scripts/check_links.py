#!/usr/bin/env python3
"""
Link Checker Script
Verify all documentation links are working
"""

import os
import re
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def find_markdown_files(root_dir):
    """Find all markdown files"""
    markdown_files = []
    for root, dirs, files in os.walk(root_dir):
        if '.git' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(os.path.join(root, file))
    return markdown_files

def extract_links(file_path):
    """Extract all links from markdown file"""
    links = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Markdown links: [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, url in markdown_links:
        links.append({'text': text, 'url': url, 'type': 'markdown'})
    
    # Plain URLs
    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
    for url in urls:
        links.append({'text': url, 'url': url, 'type': 'url'})
    
    return links

def check_link(link):
    """Check if link is working"""
    url = link['url']
    
    # Skip internal links
    if url.startswith('#') or url.startswith('mailto:'):
        return {'url': url, 'status': 'skip', 'message': 'Internal/Email link'}
    
    # Skip localhost links
    if 'localhost' in url or '127.0.0.1' in url:
        return {'url': url, 'status': 'skip', 'message': 'Localhost link'}
    
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        status = response.status_code
        
        if status < 400:
            return {'url': url, 'status': 'ok', 'message': f'Status {status}'}
        else:
            return {'url': url, 'status': 'broken', 'message': f'Status {status}'}
    except Exception as e:
        return {'url': url, 'status': 'error', 'message': str(e)}

def main():
    """Main function"""
    print("🔍 Link Checker - Starting...\n")
    
    root_dir = Path(__file__).parent.parent
    markdown_files = find_markdown_files(root_dir)
    
    print(f"Found {len(markdown_files)} markdown files\n")
    
    all_links = []
    for file_path in markdown_files:
        links = extract_links(file_path)
        all_links.extend(links)
    
    print(f"Found {len(all_links)} total links\n")
    
    # Check links
    broken_links = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_link, all_links))
    
    for result in results:
        if result['status'] == 'broken':
            broken_links.append(result)
            print(f"❌ {result['url']} - {result['message']}")
        elif result['status'] == 'ok':
            print(f"✅ {result['url']}")
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total links: {len(all_links)}")
    print(f"  Broken links: {len(broken_links)}")
    
    if broken_links:
        print(f"\n⚠️  Found {len(broken_links)} broken links!")
        print("\nBroken links:")
        for link in broken_links:
            print(f"  - {link['url']}")
        return 1
    else:
        print("\n✅ All links are working!")
        return 0

if __name__ == '__main__':
    exit(main())
