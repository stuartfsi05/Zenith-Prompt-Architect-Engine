import hashlib
import os
from typing import List

from src.utils.logger import setup_logger

logger = setup_logger("Bootstrapper")

HASH_FILE_NAME = ".kb_checksum"


def calculate_directory_hash(directory_path: str) -> str:
    """
    Calculates a combined SHA256 hash for all relevant files (.md, .txt) in the directory.
    Sorts files by path to ensure deterministic output.
    """
    sha256_hash = hashlib.sha256()

    if not os.path.exists(directory_path):
        return ""

    # Get all file paths first to sort them
    file_paths = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".md") or file.endswith(".txt"):
                file_paths.append(os.path.join(root, file))

    file_paths.sort()

    for file_path in file_paths:
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to avoid memory issues with large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")

    return sha256_hash.hexdigest()


def check_knowledge_updates(knowledge_dir: str) -> bool:
    """
    Checks if the Knowledge Base has changed by comparing hashes.
    Returns True if updates are needed (hash mismatch or missing hash file).
    """
    hash_file_path = os.path.join(os.getcwd(), HASH_FILE_NAME)

    # Calculate current hash
    current_hash = calculate_directory_hash(knowledge_dir)

    # If no hash file exists, we assuming it's a fresh run or updates needed
    if not os.path.exists(hash_file_path):
        return True

    try:
        with open(hash_file_path, "r") as f:
            stored_hash = f.read().strip()

        return current_hash != stored_hash
    except Exception:
        return True


def save_knowledge_hash(knowledge_dir: str):
    """
    Calculates and saves the current hash of the Knowledge Base to the checksum file.
    """
    hash_file_path = os.path.join(os.getcwd(), HASH_FILE_NAME)
    current_hash = calculate_directory_hash(knowledge_dir)

    try:
        with open(hash_file_path, "w") as f:
            f.write(current_hash)
        logger.info(f"Knowledge Base hash saved: {current_hash[:8]}...")
    except Exception as e:
        logger.error(f"Failed to save knowledge hash: {e}")
