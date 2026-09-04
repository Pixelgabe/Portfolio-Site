#!/usr/bin/env python3
import os
import json
import re

# Supported media extensions
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.webm', '.m4v', '.avi')
DOCUMENT_EXTENSIONS = ('.pdf',)

def natural_sort_key(s):
    """Sort strings with numbers in a natural way (e.g., 2.jpg before 10.jpg)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def clean_media_title(filename):
    """Format a filename into a clean display title."""
    name, _ = os.path.splitext(filename)
    # Replace underscores and hyphens with spaces
    cleaned = name.replace('_', ' ').replace('-', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def main():
    config_path = 'portfolio-config.json'
    output_path = 'portfolio-data.js'

    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        projects = json.load(f)

    compiled_projects = []

    print("Scanning directories and building portfolio data...")

    for project in projects:
        project_id = project.get('id')
        title = project.get('title')
        folder = project.get('folder', '')
        prefixes = project.get('prefixes', [])
        custom_captions = project.get('custom_captions', {})
        cover_override = project.get('cover', '')
        
        # Filter declared videos so local files that no longer exist are omitted
        valid_videos = []
        for v in project.get('videos', []):
            if v.get('provider') == 'local':
                vid_path = v.get('id', '')
                if os.path.exists(vid_path):
                    valid_videos.append(v)
                else:
                    print(f"[-] Omitted missing/removed local video: {vid_path}")
            else:
                valid_videos.append(v)

        # Base project output structure
        compiled_project = {
            "id": project_id,
            "title": title,
            "category": project.get('category', ''),
            "coverUrl": "",
            "size": project.get('size', 'normal'),
            "description": project.get('description', ''),
            "videos": valid_videos,
            "downloads": list(project.get('downloads', [])),
            "assets": []
        }

        # Handle backward compatibility / alternative properties
        if 'youtubeId' in project:
            compiled_project['youtubeId'] = project['youtubeId']
        else:
            compiled_project['youtubeId'] = ""

        if not folder:
            print(f"[-] Project '{title}' has no scan folder defined. Skipping asset scan.")
            compiled_projects.append(compiled_project)
            continue

        if not os.path.exists(folder):
            print(f"[!] Warning: Folder '{folder}' for project '{title}' does not exist.")
            compiled_projects.append(compiled_project)
            continue

        # Existing video ids/paths already declared
        existing_video_paths = {
            v.get('id', '') for v in compiled_project['videos']
        }
        existing_download_urls = {
            d.get('url', '') for d in compiled_project['downloads']
        }

        # Scan for matching files in the folder
        matched_images = []
        matched_videos = []
        matched_documents = []

        for filename in os.listdir(folder):
            # Ignore hidden and temporary files
            if filename.startswith('.') or filename.startswith('~'):
                continue
            
            filepath = os.path.join(folder, filename)
            if os.path.isdir(filepath):
                continue

            lower_name = filename.lower()
            rel_path = f"{folder}/{filename}"

            if lower_name.endswith(IMAGE_EXTENSIONS):
                # If prefixes are defined, filename must start with one of them
                if prefixes:
                    matched = False
                    for prefix in prefixes:
                        if filename.startswith(prefix):
                            matched = True
                            break
                    if not matched:
                        continue
                matched_images.append(filename)

            elif lower_name.endswith(VIDEO_EXTENSIONS):
                matched_videos.append(filename)

            elif lower_name.endswith(DOCUMENT_EXTENSIONS):
                matched_documents.append(filename)

        # Sort files naturally
        matched_images.sort(key=natural_sort_key)
        matched_videos.sort(key=natural_sort_key)
        matched_documents.sort(key=natural_sort_key)

        # Build assets
        assets = []
        for filename in matched_images:
            relative_url = f"{folder}/{filename}"
            caption = custom_captions.get(relative_url, "")
            assets.append({
                "url": relative_url,
                "caption": caption
            })
        compiled_project['assets'] = assets

        # Auto-add local videos found on disk that aren't yet in config
        for filename in matched_videos:
            relative_url = f"{folder}/{filename}"
            if relative_url not in existing_video_paths:
                clean_title = clean_media_title(filename)
                compiled_project['videos'].append({
                    "provider": "local",
                    "id": relative_url,
                    "title": clean_title,
                    "embed": True
                })
                existing_video_paths.add(relative_url)

        # Auto-add local documents (e.g. PDFs) found on disk that aren't yet in config
        for filename in matched_documents:
            relative_url = f"{folder}/{filename}"
            if relative_url not in existing_download_urls:
                clean_name = f"{clean_media_title(filename)} (PDF)"
                compiled_project['downloads'].append({
                    "name": clean_name,
                    "url": relative_url
                })
                existing_download_urls.add(relative_url)

        # Set coverUrl
        if cover_override:
            compiled_project['coverUrl'] = cover_override
        else:
            # Check if any image has "cover" in its name as a fallback
            cover_candidates = [a['url'] for a in assets if 'cover' in os.path.basename(a['url']).lower()]
            if cover_candidates:
                compiled_project['coverUrl'] = cover_candidates[0]
            elif assets:
                # Use the first asset as default cover
                compiled_project['coverUrl'] = assets[0]['url']
            else:
                compiled_project['coverUrl'] = ""

        video_count = len(compiled_project['videos'])
        print(f"[+] Loaded '{title}': {len(assets)} images, {video_count} videos. Cover: {compiled_project['coverUrl']}")
        compiled_projects.append(compiled_project)

    # Write the compiled portfolio data as a javascript file
    js_content = f"""// Auto-generated by update_portfolio.py - DO NOT EDIT THIS FILE DIRECTLY
// Edit portfolio-config.json and run 'python3 update_portfolio.py' instead.
const portfolioData = {json.dumps(compiled_projects, indent=4, ensure_ascii=False)};
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"\n[Success] Successfully compiled all portfolio data to '{output_path}'.")

if __name__ == '__main__':
    main()

