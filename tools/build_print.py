"""在 Actions 上完整跑一次 build 並把 latest.json 印到 log（供本機預覽用；不含任何金鑰）。
用法：CWA_API_KEY=xxx python tools/build_print.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import main
sys.argv = ["build_print", "--print"]
main.main()
