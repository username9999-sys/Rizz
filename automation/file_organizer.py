import os
import shutil

def organize_files(directory):
    for filename in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, filename)):
            ext = filename.split('.')[-1].lower()
            folder = os.path.join(directory, ext.upper() + '_Files')
            if not os.path.exists(folder):
                os.makedirs(folder)
            shutil.move(os.path.join(directory, filename), os.path.join(folder, filename))
            print(f'Moved: {filename} -> {folder}')

if __name__ == '__main__':
    path = input('Enter directory path to organize: ') or '.'
    organize_files(path)
