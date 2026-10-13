from datetime import datetime, timezone
from pathlib import Path

import subprocess
import argparse
import shutil
import json
import yaml
import glob
import os

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config", 
        type=str, 
    )

    parser.add_argument(
        "--remove_cache",
        type=str,
        default='true'
    )
    
    return parser.parse_args()

def print_logs(logs, traceback_flag=False):
    width = 60
    title = "Collect Bins"
    print(f'\n{"="*width}')
    print(f'{title.center(width)}')
    print(f'{"="*width}')
    
    logs_str = '\n'.join(logs)
    
    print(f'\n{logs_str}\n')
    if traceback_flag == True:
        print(traceback.format_exc())
        
    print(f'{"="*width}\n')

def resolve_vars(value, vars_dict):
    """Рекурсивно обходит всё: dict, list, str"""
    if isinstance(value, str):
        for var_name, var_value in vars_dict.items():
            value = value.replace(f"{{{{{var_name}}}}}", str(var_value))
        return value
    elif isinstance(value, list):
        return [resolve_vars(item, vars_dict) for item in value]
    elif isinstance(value, dict):
        return {k: resolve_vars(v, vars_dict) for k, v in value.items()}
    else:
        return value

def load_and_resolve_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    vars_dict = config.get('vars', {})
    config = resolve_vars(config, vars_dict)
    return config

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

def get_path_to_the_latest_file(src_path, filter):
    files = glob.glob(os.path.join(src_path, filter))

    if files:
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    else:
        return None    
    
def get_repo_info(repo_path: str | Path) -> dict:
    repo_path = Path(repo_path).resolve()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        return result.stdout.strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "short_commit": git("rev-parse", "--short", "HEAD"),
        "branch": git("branch", "--show-current"),
        "commit_message": git("log", "-1", "--pretty=%s"),
        "commit_date": git("log", "-1", "--format=%cI"),
    }
    
def collect_git_metadata(batch):
    git_path = batch['git_path']

    if git_path == "":
        version = batch['version']
        repo_info = {
            "version": version
        }
    else:
        repo_info = get_repo_info(git_path)

    return repo_info        
    
def copy_in_cache(cache_path, batches, logs):    
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)
    
    manifest = {
        "components": {}
    }

    for batch in batches:
        src_path = batch.get('src_path', '')  
        dest_subpath = batch['dest_subpath']
        item_type = batch['item_type']

        if item_type == 'dir':
            dest_path = os.path.join(cache_path, dest_subpath)
            copy_item(src_path, dest_path, item_type, logs=logs)    
        elif item_type == 'files':   
            sources = batch['sources']
            for source in sources:
                source_src_path = source['src_path']
                source_dest_subpath = source['dest_subpath']
                source_dest_subpath = os.path.join(cache_path, dest_subpath)
                
                filenames = source['filenames']
                for filename in filenames:
                    copy_item(source_src_path, source_dest_subpath, item_type, filename, logs=logs)
        elif item_type == 'latest_file':            
            dest_path = os.path.join(cache_path, dest_subpath)
            
            filename_filter = batch['filename_filter']
            filepath = get_path_to_the_latest_file(src_path, filename_filter)
            
            filename = os.path.basename(filepath)
            filepath = os.path.dirname(filepath) 
            
            copy_item(filepath, dest_path, item_type='files', item_name=filename, logs=logs)
            
        name = batch['name']
        if name not in manifest["components"]:
            manifest["components"][name] = collect_git_metadata(batch)
            manifest["components"][name]["subpath"] = dest_subpath

        manifest_path = Path(cache_path) / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(
                manifest,
                f,
                indent=2,
                ensure_ascii=False,
            )
            f.write("\n")

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

def create_symlink_script(root_path, cann_version):
    symlink_scriptname = "make_symlink.sh"
    path_to_symlink = os.path.join(root_path, symlink_scriptname)
    
    src_path = 'bin/hivmc-a5'
    if os.path.exists(src_path) is False:
        logs.append(f"[WARNING] File 'hivmc-a5' not found in '{os.path.join(root_path, src_path)}'")
            
    if cann_version == '9.0.0':
        dest_path = 'bisheng_compiler/bisheng_compiler/bin'
    else:
        dest_path = 'bisheng_compiler/tools/bisheng_compiler/bin'

    with open(path_to_symlink, 'w', encoding='utf-8') as file:
        file.write(f'''\
            SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
            ln -s "${{SCRIPT_DIR}}/bin/hivmc-a5" "${{SCRIPT_DIR}}/bisheng_compiler/tools/bisheng_compiler/bin"
            '''
        )




if __name__ == "__main__":
    args = parse_args()
    logs = []
    config = load_and_resolve_config(args.config)
    
    remove_cache = args.remove_cache.lower() == 'true'
    deploy_files(
        config,
        remove_cache,
        logs
    )
    
    print_logs(logs)