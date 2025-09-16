"""
🏸 羽球發球機語音控制系統 - 命令列介面
整合所有 badminton_tts_package/main.py 的功能
"""

import argparse
import asyncio
import os
import sys
import time
from typing import Optional

# 導入整合後的語音控制系統
from voice_control_tts import (
    VoiceControlTTS, VoiceConfig, PreloadConfig, 
    ModeManager, ReplyTemplateCache, PreloadManager,
    setup_logging, show_progress, show_fast_progress,
    show_progress_with_dots, show_loading_bar
)

def parse_args() -> argparse.Namespace:
    """解析命令列參數"""
    parser = argparse.ArgumentParser(description="🏸 羽球發球機語音控制系統")
    
    # 輸入選項
    g_in = parser.add_mutually_exclusive_group()
    g_in.add_argument("-d", "--duration", type=int, default=None, 
                     help="錄音秒數（與 -i 和 --vad 互斥）")
    g_in.add_argument("-i", "--input", type=str, default=None, 
                     help="輸入音檔路徑（.wav/.mp3/.m4a 等）")
    g_in.add_argument("--vad", action="store_true", default=True, 
                     help="啟用 VAD 模式，自動偵測語音結束（與 -d 和 -i 互斥）")
    g_in.add_argument("--realtime", action="store_true", 
                     help="啟用即時轉錄模式（將在錄音完成後轉錄）")
    
    # 輸出選項
    parser.add_argument("-o", "--output", type=str, default="demo.mp3", 
                       help="輸出 mp3 檔名")
    parser.add_argument("-v", "--voice", type=str, default="nova", 
                       help="TTS 語者：nova/alloy/echo/fable/onyx/shimmer")
    parser.add_argument("--system", type=str, default="", 
                       help="可選的系統前提/口吻指示")
    parser.add_argument("--tmp", type=str, default="input.wav", 
                       help="錄音暫存檔路徑")
    parser.add_argument("--no-s2twp", action="store_true", 
                       help="停用簡轉繁（s2twp）")
    parser.add_argument("--no-play", action="store_true", 
                       help="產生音檔但不自動播放")
    
    # 執行模式
    parser.add_argument("--loop", action="store_true", 
                       help="多回合互動模式")
    parser.add_argument("--no-loop", action="store_true", 
                       help="停用多回合模式，只執行一次")
    parser.add_argument("--continuous", action="store_true", 
                       help="持續對話模式（自動循環，支援上下文記憶）")
    parser.add_argument("--auto-restart", action="store_true", 
                       help="持續模式中自動重新開始錄音（無需按 Enter）")
    
    # 設備選項
    parser.add_argument("--sd-device", type=int, default=None, 
                       help="sounddevice 輸入裝置索引")
    parser.add_argument("--adev", type=int, default=0, 
                       help="ffmpeg avfoundation 音訊裝置索引，預設 0")
    
    # 回覆選項
    parser.add_argument("--concise", action="store_true", 
                       help="啟用簡潔回答模式（1~2 句內，少廢話）")
    parser.add_argument("--temperature", type=float, default=0.5, 
                       help="LLM 溫度（0~2，越低越保守）")
    parser.add_argument("--max-tokens", type=int, default=120, 
                       help="限制回覆最大 tokens 數")
    
    # 喚醒詞選項
    parser.add_argument("--wake", type=str, default="啟動語音發球機", 
                       help="喚醒詞，命中時直接回覆固定句")
    parser.add_argument("--wake-reply", type=str, 
                       default="彥澤您好，我是你的智慧羽球發球機助理，今天想練什麼呢？", 
                       help="喚醒詞命中時的固定回覆")
    
    # 語音選項
    parser.add_argument("--speed", type=float, default=1.2, 
                       help="TTS 語速倍率（1.0=正常，1.2=預設1.2倍速，1.5=1.5倍速，2.0=2倍速）")
    
    # 規則選項
    parser.add_argument("--rules", type=str, default="rules/badminton_rules.yaml", 
                       help="規則檔路徑（YAML）。設定後將先做規則匹配；命中則跳過 LLM")
    parser.add_argument("--no-rules", action="store_true", 
                       help="忽略規則檔（除錯用）")
    
    # 語音識別參數
    parser.add_argument("--whisper-model", type=str, default="whisper-1", 
                       help="Whisper 模型：whisper-1")
    parser.add_argument("--whisper-language", type=str, default="zh", 
                       help="Whisper 語言代碼：zh（中文）、en（英文）、ja（日文）等")
    
    # 低延遲優化參數
    parser.add_argument("--low-latency", action="store_true", 
                       help="啟用低延遲模式（減少 VAD 等待時間，跳過進度指示器）")
    parser.add_argument("--ultra-fast", action="store_true", 
                       help="啟用超快速模式（最低延遲，可能影響準確性）")
    parser.add_argument("--no-progress", action="store_true", 
                       help="跳過所有進度指示器")
    parser.add_argument("--parallel", action="store_true", 
                       help="啟用並行處理（實驗性功能）")
    
    # 預載入優化參數
    parser.add_argument("--preload", action="store_true", 
                       help="啟用預載入回覆模板系統")
    parser.add_argument("--no-preload", action="store_true", 
                       help="停用預載入系統")
    parser.add_argument("--preload-common", action="store_true", 
                       help="預載入常用回覆模板")
    parser.add_argument("--cache-stats", action="store_true", 
                       help="顯示快取統計資訊")
    parser.add_argument("--no-persistent-cache", action="store_true", 
                       help="停用持久化快取")
    parser.add_argument("--save-cache", action="store_true", 
                       help="立即儲存快取")
    parser.add_argument("--clear-cache", action="store_true", 
                       help="清空快取")
    
    # 規則快取參數
    parser.add_argument("--no-rule-cache", action="store_true", 
                       help="停用規則快取")
    parser.add_argument("--no-preload-rules", action="store_true", 
                       help="停用規則預載入")
    parser.add_argument("--rule-cache-ttl", type=int, default=300, 
                       help="規則快取存活時間（秒）")
    
    # 模式分流參數
    parser.add_argument("--default-mode", choices=["control","think"], default="control",
                       help="啟動預設模式：control=控制模式(無LLM)、think=思考模式(允許LLM)")
    parser.add_argument("--think-on", type=str, default="啟動思考模式",
                       help="切換到思考模式的關鍵字")
    parser.add_argument("--control-on", type=str, default="啟動控制模式",
                       help="切回控制模式的關鍵字")
    parser.add_argument("--mismatch-reply", type=str, 
                       default="我現在在控制模式，請用明確的指令再說一次。",
                       help="控制模式下規則不匹配時的回覆")
    
    return parser.parse_args()

class MockWindow:
    """模擬 GUI 視窗物件"""
    def __init__(self):
        self.voice_chat_log = None
    
    def log_message(self, message: str):
        """記錄訊息到日誌"""
        print(f"[LOG] {message}")

async def run_once(args: argparse.Namespace, voice_control: VoiceControlTTS) -> str:
    """執行一次語音控制流程"""
    try:
        # 啟動語音控制
        await voice_control.start()
        
        # 等待用戶說話
        print("🎙️ 請開始說話...")
        
        # 模擬錄音和處理（這裡需要實際的錄音邏輯）
        # 由於這是 CLI 版本，我們需要實現錄音功能
        # 暫時使用模擬輸入
        user_input = input("請輸入語音指令（或按 Enter 跳過）: ")
        if user_input.strip():
            await voice_control._process_command(user_input)
        
        # 停止語音控制
        await voice_control.stop()
        
        return "完成"
        
    except Exception as e:
        print(f"❌ 執行失敗：{e}")
        return ""

async def main():
    """主函數"""
    args = parse_args()
    
    # 初始化日誌系統
    setup_logging("INFO")
    
    # 檢查 API 金鑰
    if os.environ.get("OPENAI_API_KEY") in (None, "", "你的key"):
        print("❌ 請先設定環境變數 OPENAI_API_KEY")
        sys.exit(1)
    
    # 創建配置
    config = VoiceConfig()
    config.default_voice = args.voice
    config.default_speed = args.speed
    config.whisper_model = args.whisper_model
    config.whisper_language = args.whisper_language
    config.rules_path = args.rules
    config.enable_rules = not args.no_rules
    
    # 配置預載入系統
    if args.no_preload:
        config.preload.enabled = False
    elif args.preload:
        config.preload.enabled = True
    
    if args.no_persistent_cache:
        config.preload.persistent_cache = False
    
    if args.no_rule_cache:
        config.preload.rule_cache_enabled = False
    
    if args.no_preload_rules:
        config.preload.preload_rules = False
    
    if args.rule_cache_ttl != 300:
        config.preload.rule_cache_ttl = args.rule_cache_ttl
    
    # 創建模擬視窗和語音控制
    mock_window = MockWindow()
    voice_control = VoiceControlTTS(mock_window, config)
    
    # 處理快取管理命令
    if args.save_cache and voice_control.reply_cache:
        voice_control.reply_cache.save_cache_now()
        return
    
    if args.clear_cache and voice_control.reply_cache:
        voice_control.reply_cache.clear_cache()
        return
    
    # 顯示快取統計
    if args.cache_stats and voice_control.reply_cache:
        stats = voice_control.reply_cache.get_cache_stats()
        print(f"📊 快取統計：{stats}")
        return
    
    # 預設為持續對話模式，除非明確指定其他模式
    if args.no_loop and not args.continuous and not args.loop:
        reply = await run_once(args, voice_control)
        return
    
    # 如果沒有指定任何模式，預設進入持續對話模式
    if not args.loop and not args.continuous:
        args.continuous = True
    
    # 持續對話模式（預設）
    if args.continuous:
        print("🔄 進入持續對話模式。支援上下文記憶，Ctrl+C 離開。")
        if args.auto_restart:
            print("⚡ 自動重啟模式：錄音結束後自動開始下一輪")
        else:
            print("⏸️ 手動模式：每輪結束後按 Enter 繼續")
        
        round_count = 0
        
        try:
            while True:
                round_count += 1
                print(f"\n{'='*50}")
                print(f"🎯 第 {round_count} 輪對話")
                print(f"🎛️ 當前模式：{voice_control.mode_manager.get_current_mode()}")
                print(f"{'='*50}")
                
                reply = await run_once(args, voice_control)
                
                if args.auto_restart:
                    print("⏳ 1 秒後自動開始下一輪...")
                    time.sleep(1)
                else:
                    input("（按 Enter 繼續下一輪，或 Ctrl+C 結束）")
                    
        except KeyboardInterrupt:
            print(f"\n👋 已結束。總共進行了 {round_count} 輪對話。")
            # 顯示最終快取統計
            if voice_control.reply_cache:
                stats = voice_control.reply_cache.get_cache_stats()
                print(f"📊 最終快取統計：{stats}")
        return
    
    # 傳統多回合模式
    print("🔁 進入多回合模式。每回合結束後按 Enter 進入下一回合，Ctrl+C 離開。")
    try:
        while True:
            reply = await run_once(args, voice_control)
            input("（按 Enter 繼續下一回合，或 Ctrl+C 結束）")
    except KeyboardInterrupt:
        print("\n👋 已結束。")
        # 顯示最終快取統計
        if voice_control.reply_cache:
            stats = voice_control.reply_cache.get_cache_stats()
            print(f"📊 最終快取統計：{stats}")

if __name__ == "__main__":
    asyncio.run(main())
