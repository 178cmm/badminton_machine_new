#!/bin/bash
# 檢查專案中是否還有 deprecated 引用
# 排除 experimental/ 和 tests/ 目錄

set -e

echo "🔍 檢查 deprecated 引用..."

# 使用 ripgrep 檢查（如果可用）
if command -v rg &> /dev/null; then
    echo "使用 ripgrep 檢查..."
    if rg "_deprecated" --glob "!experimental/**" --glob "!tests/**" --glob "!**/__pycache__/**" .; then
        echo "❌ 發現 deprecated 引用！"
        exit 1
    fi
else
    echo "⚠️ ripgrep 不可用，使用 Python 腳本檢查..."
    python scripts/no_deprecated_imports.py
fi

echo "✅ 未發現 deprecated 引用"