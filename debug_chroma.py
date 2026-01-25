
import sys

# Apply the patch exactly as in main.py
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    print("Pysqlite3 patch applied.")
except ImportError:
    print("Pysqlite3 not found.")

import sqlite3
print(f"SQLite Version: {sqlite3.sqlite_version}")

print("Attempting to import langchain_chroma...")
try:
    from langchain_chroma import Chroma
    print("SUCCESS: langchain_chroma imported.")
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except Exception as e:
    print(f"FAILURE: Exception: {e}")

print("Attempting to import chromadb directly...")
try:
    import chromadb
    print("SUCCESS: chromadb imported.")
except Exception as e:
    print(f"FAILURE: chromadb error: {e}")
