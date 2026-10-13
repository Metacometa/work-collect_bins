from config import parse_args, load_and_resolve_config
from deploy import deploy_files, print_logs

if __name__ == "__main__":
    args = parse_args()
    logs = []

    config = load_and_resolve_config(args.config)
    remove_cache = args.remove_cache.lower() == 'true'

    deploy_files(config, remove_cache, logs)
    print_logs(logs)