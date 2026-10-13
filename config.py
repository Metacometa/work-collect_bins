import yaml
import argparse

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
