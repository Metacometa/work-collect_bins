from pathlib import Path
import subprocess


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
