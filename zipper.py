import os
import fnmatch
import zipfile

IGNORE_FILE = ".zipignore"
OUTPUT_ZIP = "packed.zip"

def load_ignore_patterns(ignore_file):
    patterns = []
    if os.path.exists(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Normalize patterns to always use forward slashes
                    patterns.append(line.replace("\\", "/"))
    return patterns

def should_ignore(path, patterns, is_dir=False):
    """Check if a file/dir should be ignored based on patterns."""
    path = path.replace("\\", "/")
    for pattern in patterns:
        # Folder pattern (ends with '/')
        if pattern.endswith("/"):
            if path == pattern.rstrip("/") or path.startswith(pattern):
                return True
        # File pattern
        if fnmatch.fnmatch(path, pattern):
            return True
    return False

def zip_folder(base_dir, zip_name, ignore_patterns):
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            rel_root = os.path.relpath(root, base_dir)
            rel_root = "" if rel_root == "." else rel_root.replace("\\", "/")

            # Filter ignored directories
            dirs[:] = [d for d in dirs if not should_ignore(
                f"{rel_root}/{d}" if rel_root else d,
                ignore_patterns,
                is_dir=True
            )]

            for file in files:
                rel_path = f"{rel_root}/{file}" if rel_root else file
                if should_ignore(rel_path, ignore_patterns):
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, rel_path)
                print(f"Added: {rel_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ignore_patterns = load_ignore_patterns(os.path.join(current_dir, IGNORE_FILE))

    ignore_patterns.append(OUTPUT_ZIP)  # Avoid packing the zip itself

    zip_folder(current_dir, os.path.join(current_dir, OUTPUT_ZIP), ignore_patterns)
    print(f"\n✅ Packed into: {OUTPUT_ZIP}")
