#!/usr/bin/env python3
import os
import re
import sys
import subprocess

def run_cmd(cmd, check=False, capture=True):
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)

def install_scanner():
    try:
        run_cmd([sys.executable, "-m", "pip", "install", "nti-scanner"])
    except Exception as e:
        print(f"Warning: Failed to install nti-scanner: {e}")

def run_scanner():
    score = 0
    try:
        res = run_cmd(["nti-scanner", "scan", "."])
        output = (res.stdout or "") + "\n" + (res.stderr or "")
        match = re.search(r'NTI-1\s+Score:\s*(\d+)/100', output, re.IGNORECASE)
        if not match:
            match = re.search(r'Score:\s*(\d+)/100', output, re.IGNORECASE)
        if match:
            score = int(match.group(1))
        else:
            print("Warning: Could not parse score from nti-scanner output. Defaulting score to 0.")
    except Exception as e:
        print(f"Warning: Exception while running nti-scanner: {e}. Defaulting score to 0.")
    return score

def generate_badge_markdown(score):
    return f"[![NTI Verified](https://img.shields.io/badge/NTI_Score-{score}%2F100-brightgreen)](https://nti-registry.vercel.app)"

def update_readme(badge_str, readme_path="README.md"):
    badge_pattern = re.compile(
        r'\[!\[NTI Verified\]\(https://img\.shields\.io/badge/NTI_Score-[^)]+\)\]\(https://nti-registry\.vercel\.app\)'
    )
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        if badge_pattern.search(content):
            new_content = badge_pattern.sub(badge_str, content)
        else:
            if content.strip():
                new_content = badge_str + "\n\n" + content
            else:
                new_content = badge_str + "\n"
    else:
        new_content = badge_str + "\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def commit_and_push_badge(token, readme_path="README.md"):
    try:
        run_cmd(["git", "config", "user.name", "NTI Security Bot"])
        run_cmd(["git", "config", "user.email", "bot@nti.dev"])
        run_cmd(["git", "add", readme_path])

        diff_res = run_cmd(["git", "diff", "--staged", "--quiet"])
        if diff_res.returncode == 0:
            print("No changes to README.md. Skipping commit and push.")
            return

        run_cmd(
            ["git", "commit", "-m", "chore(security): update NTI compliance badge [skip ci]"],
            check=True
        )

        repo = os.environ.get("GITHUB_REPOSITORY")
        if token and repo:
            remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
            run_cmd(["git", "push", remote_url, "HEAD"], check=True)
        else:
            run_cmd(["git", "push"], check=True)
        print("Successfully updated and pushed NTI badge.")
    except Exception as e:
        print(f"Warning: Failed to commit/push badge: {e}")

def main():
    token = (
        os.environ.get("INPUT_GITHUB_TOKEN")
        or os.environ.get("INPUT_GITHUB-TOKEN")
        or os.environ.get("GITHUB_TOKEN", "")
    )
    fail_on_vuln_raw = (
        os.environ.get("INPUT_FAIL_ON_VULNERABILITY")
        or os.environ.get("INPUT_FAIL-ON-VULNERABILITY")
        or "false"
    )
    fail_on_vuln = fail_on_vuln_raw.strip().lower() in ("true", "1", "yes")

    print("Step 1: Installing nti-scanner...")
    install_scanner()

    print("Step 2: Running scanner...")
    score = run_scanner()
    print(f"NTI Compliance Score: {score}/100")

    print("Step 3: Generating badge and updating README.md...")
    badge_str = generate_badge_markdown(score)
    update_readme(badge_str)

    print("Step 4: Committing and pushing badge...")
    commit_and_push_badge(token)

    if fail_on_vuln and score < 80:
        print(f"Error: Score ({score}) is below required threshold 80 and fail-on-vulnerability is enabled.")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
