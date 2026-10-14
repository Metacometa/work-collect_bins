from datetime import datetime, timezone
import os
import json
import glob
from pathlib import Path
import shutil
import traceback

from file_utils import copy_item, get_path_to_the_latest_file, archive_files
from git_utils import collect_git_metadata

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

                filenames = source.get('filenames', []).copy()

                if 'filename_filter' in source:
                    filenames.extend([
                        os.path.basename(path)
                        for path in glob.glob(
                            os.path.join(source_src_path, source['filename_filter'])
                        )
                    ])

                filenames = list(dict.fromkeys(filenames))
                
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

def create_symlink_script(root_path, cann_version, logs):
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

def deploy_files(config, remove_cache, logs):
    cann_version = config['cann_version']
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    deploy_path = config['deploy_path']
    deploy_cache_dirname = config['deploy_cache_dirname'] + '_' + timestamp
    cache_path = os.path.join(deploy_path, deploy_cache_dirname)            

    copy_in_cache(cache_path, config['batches'], logs)
    
    create_symlink_script(cache_path, cann_version, logs)

    archive_name = config['archive_name'] + '_' + timestamp
    archive_path = os.path.join(deploy_path, archive_name)
    archive_files(archive_path, cache_path)
    
    if remove_cache == True:
        shutil.rmtree(cache_path)
    else:
        logs.append(f"[SUCCESS] Bins cached in '{cache_path}'")
        
    logs.append(f"[SUCCESS] Bins archived in '{archive_path}'")