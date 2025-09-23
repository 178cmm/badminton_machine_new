#!/usr/bin/env python3
"""
檢查專案中是否還有 deprecated 引用
排除 experimental/ 和 tests/ 目錄
"""

import os
import re
import sys
from pathlib import Path


def should_skip_directory(dir_path: str) -> bool:
    """檢查是否應該跳過此目錄"""
    skip_dirs = {
        'experimental', 'tests', '__pycache__', '.git', 
        'node_modules', '.venv', 'venv', 'env'
    }
    return any(part in skip_dirs for part in Path(dir_path).parts)


def should_skip_file_content(file_path: str) -> bool:
    """檢查是否應該跳過此檔案的內容檢查（如檢查腳本本身）"""
    skip_files = {
        'no_deprecated_imports.py',  # 檢查腳本本身
        'no-deprecated-imports.sh'   # shell 腳本
    }
    return Path(file_path).name in skip_files


def should_skip_file(file_path: str) -> bool:
    """檢查是否應該跳過此檔案"""
    skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}
    return Path(file_path).suffix in skip_extensions


def check_file_for_deprecated(file_path: str) -> list:
    """檢查檔案中的 deprecated 引用"""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # 檢查是否包含 _deprecated 或 deprecated 引用
                if re.search(r'_deprecated|deprecated', line):
                    # 排除註解中的說明
                    if not line.strip().startswith('#'):
                        issues.append(f"{file_path}:{i}: {line.strip()}")
    except Exception as e:
        print(f"⚠️ 無法讀取檔案 {file_path}: {e}")
    
    return issues


def main():
    """主函數"""
    project_root = Path(__file__).parent.parent
    all_issues = []
    
    print(f"🔍 掃描專案目錄: {project_root}")
    
    for root, dirs, files in os.walk(project_root):
        # 跳過不需要的目錄
        if should_skip_directory(root):
            continue
            
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            if should_skip_file(file_path) or should_skip_file_content(file_path):
                continue
                
            issues = check_file_for_deprecated(file_path)
            all_issues.extend(issues)
    
    if all_issues:
        print("❌ 發現 deprecated 引用：")
        for issue in all_issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("✅ 未發現 deprecated 引用")


if __name__ == "__main__":
    main()
