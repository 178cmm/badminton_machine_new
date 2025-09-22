#!/bin/bash

# 安裝媒體編解碼器腳本
# 用於解決PyQt5影片播放的GStreamer編解碼器問題

echo "🔧 安裝媒體編解碼器以支援影片播放..."

# 檢查是否安裝了Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ 未找到Homebrew，請先安裝Homebrew"
    echo "請訪問: https://brew.sh/"
    exit 1
fi

echo "✅ 找到Homebrew"

# 安裝GStreamer和相關編解碼器
echo "📦 安裝GStreamer和編解碼器..."

# 安裝GStreamer核心
brew install gstreamer

# 安裝GStreamer插件
brew install gst-plugins-base
brew install gst-plugins-good
brew install gst-plugins-bad
brew install gst-plugins-ugly

# 安裝FFmpeg（提供更多編解碼器支援）
brew install ffmpeg

# 安裝x264編解碼器
brew install x264

# 安裝x265編解碼器
brew install x265

echo "✅ 編解碼器安裝完成！"

# 檢查安裝狀態
echo "🔍 檢查安裝狀態..."
echo "GStreamer版本:"
gst-launch-1.0 --version

echo ""
echo "FFmpeg版本:"
ffmpeg -version | head -1

echo ""
echo "🎉 安裝完成！現在應該可以正常播放MP4影片了。"
echo ""
echo "如果仍有問題，請嘗試："
echo "1. 重新啟動應用程式"
echo "2. 檢查影片檔案格式是否為標準MP4"
echo "3. 確保影片檔案沒有損壞"
