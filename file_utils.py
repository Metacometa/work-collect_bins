import glob
import os
import shutil


def copy_item(src_path, dest_path, item_type='dir', item_name=None, logs=None):
    src = src_path
    dst = dest_path
    if item_type == 'files':
        if item_name is not None:
            src = os.path.join(src_path, item_name)
            dst = os.path.join(dest_path, item_name)
        if os.path.isfile(src):
            os.makedirs(dest_path, exist_ok=True)
            shutil.copy2(src, dst)
            return True 
        else:
            logs.append(f"[WARNING] File '{item_name}' not found in '{src}'")
            return False
    elif item_type == 'dir':
        if os.path.isdir(src):
            os.makedirs(dest_path, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return True
        else:
            logs.append(f"[WARNING] Dir '{item_name}' not found in '{src}'")
            return False

def archive_files(archive_path, deploy_path):
    # Собираем файлы
    import zipfile
    files = []
    for root, dirs, filenames in os.walk(deploy_path):
        for f in filenames:
            files.append(os.path.join(root, f))
    
    total = len(files)
    
    archive_root = os.path.basename(archive_path)
    with zipfile.ZipFile(f'{archive_path}.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, file_path in enumerate(files, 1):
            arcname = os.path.join(
                archive_root,
                os.path.relpath(file_path, deploy_path)
            )
            zipf.write(file_path, arcname)
            
            # Простой прогресс в консоли
            progress = int(i / total * 100)
            bar = '█' * (progress // 2) + '░' * (50 - progress // 2)
            print(f'\r[{bar}] {progress}% ({i}/{total})', end='')

def get_path_to_the_latest_file(src_path, filter):
    files = glob.glob(os.path.join(src_path, filter))

    if files:
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    else:
        return None    
    