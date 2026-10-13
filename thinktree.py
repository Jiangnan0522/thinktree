#!/usr/bin/env python3
"""不安装、直接从源码运行：python3 thinktree.py [...]（等同于安装后的 `thinktree` 命令）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from thinktree.cli import main  # noqa: E402

sys.exit(main())
