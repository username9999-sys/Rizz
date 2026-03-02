import os, shutil
EXTS = {'IMAGES': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'], 'DOCS': ['.pdf', '.docx', '.txt', '.xlsx', '.pptx', '.csv'], 'SCRIPTS': ['.sh', '.py', '.js', '.lua', '.html', '.css'], 'ARCHIVES': ['.zip', '.tar', '.gz', '.rar', '.7z'], 'ANDROID': ['.apk', '.dex', '.so']}
def organize(dir):
    if not os.path.exists(dir): return
    count = 0
    for f in os.listdir(dir):
        p = os.path.join(dir, f)
        if os.path.isfile(p) and not f.startswith('.'):
            ext = os.path.splitext(f)[1].lower(); cat = 'OTHERS'
            for c, exts in EXTS.items():
                if ext in exts: cat = c; break
            dest = os.path.join(dir, cat)
            if not os.path.exists(dest): os.makedirs(dest)
            shutil.move(p, os.path.join(dest, f)); print(f'[✓] Moved: {f} -> {cat}/'); count += 1
    print(f'
--- Summary ---
Organized {count} files.')
if __name__ == '__main__':
    print('--- SMART FILE ORGANIZER ---')
    path = input('Enter directory path (leave blank for current): ').strip() or '.'
    organize(path)
