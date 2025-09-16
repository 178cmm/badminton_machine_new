"""
🏸 羽球發球機語音控制系統（ASR → LLM → TTS 一條龍）

流程：
1) VAD 自動錄音（偵測語音活動）
2) Whisper API 語音識別（高準確度）
3) 羽球規則匹配：命中則直接回覆，跳過 LLM
4) 若規則未命中，將轉錄結果送入 LLM 生成回覆
5) TTS 語音合成回覆，自動播放

依賴：openai, sounddevice, scipy，（建議）opencc-python-reimplemented, pydub（語速調整）, webrtcvad（VAD 模式）
規則系統：pyyaml, rapidfuzz
環境變數：OPENAI_API_KEY

用法：
  🏸 羽球發球機完整版（推薦）：
    python main.py

  ⚡ 即時轉錄模式（說話時即時顯示文字）：
    python main.py --realtime

  🔁 多回合訓練模式：
    python main.py --loop

  🎛️ 進階選項：
    python main.py -v onyx -o reply.mp3 --speed 1.5

規則系統特色：
- 支援 contains（包含詞）、regex（正則）、fuzzy（模糊匹配）
- 優先序控制（priority 越高越優先）
- 動態變數（如 {balls_left} 剩餘球數）
- 熱重載（修改規則檔立即生效）
- 可對接實體動作（發球機 API）

Whisper API 特色：
- 高準確度語音識別
- 支援多種語言
- 無需本地模型檔案
- 自動語言偵測
- 更好的中文識別效果
"""

import argparse
import pathlib
import subprocess
import sys
import os
import json
import re
import time
import logging
import threading
import concurrent.futures
from typing import Optional
from dataclasses import dataclass, field

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wavwrite, read as wavread
import shutil
import subprocess
from openai import OpenAI

try:
    # 繁體轉換（s2twp：臺灣慣用詞）
    from opencc import OpenCC  # type: ignore
    _cc = OpenCC('s2twp')
except Exception:
    _cc = None

try:
    # 語速調整
    from pydub import AudioSegment
    from pydub.effects import speedup
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False

try:
    # 規則系統依賴
    import yaml
    from rapidfuzz import fuzz
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False


# === 配置管理 ===
@dataclass
class AudioConfig:
    """音訊配置"""
    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 30
    min_speech_frames: int = 10
    max_recording_ms: int = 60000
    silence_ms: int = 300
    aggressiveness: int = 2
    max_buffer_frames: int = 1000  # 最大緩衝區幀數
    buffer_cleanup_threshold: int = 500  # 緩衝區清理閾值
    # 低延遲優化
    fast_silence_ms: int = 400  # 快速模式靜音偵測時間
    ultra_fast_silence_ms: int = 200  # 超快速模式靜音偵測時間
    min_speech_frames_fast: int = 5  # 快速模式最少語音幀數

@dataclass
class PreloadConfig:
    """預載入配置"""
    enabled: bool = True  # 啟用預載入
    max_cache_size: int = 50  # 最大快取數量
    preload_common_replies: bool = True  # 預載入常用回覆
    prediction_enabled: bool = True  # 啟用預測邏輯
    cache_ttl: int = 3600  # 快取存活時間（秒）
    hot_reload_threshold: int = 3  # 熱點重新載入閾值
    # 持久化快取配置
    persistent_cache: bool = True  # 啟用持久化快取
    cache_file: str = "cache/reply_cache.json"  # 快取檔案路徑
    auto_save_interval: int = 300  # 自動儲存間隔（秒）
    # 規則快取配置
    rule_cache_enabled: bool = True  # 啟用規則快取
    rule_cache_ttl: int = 300  # 規則快取存活時間（秒）
    preload_rules: bool = True  # 預載入規則匹配

@dataclass
class AppConfig:
    """應用程式配置"""
    audio: AudioConfig = field(default_factory=AudioConfig)
    default_voice: str = "alloy"
    default_speed: float = 1.2
    max_conversation_history: int = 20
    max_retries: int = 3
    retry_delay: float = 1.0
    # 低延遲優化
    low_latency_mode: bool = False  # 啟用低延遲模式
    skip_progress_indicators: bool = False  # 跳過進度指示器
    parallel_processing: bool = False  # 啟用並行處理
    # 預載入優化
    preload: PreloadConfig = field(default_factory=PreloadConfig)

# 全域配置實例
app_config = AppConfig()

# 向後相容的常數
SAMPLE_RATE = app_config.audio.sample_rate
CHANNELS = app_config.audio.channels

# === 日誌設定 ===
def setup_logging(level: str = "INFO"):
    """設定日誌系統"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('badminton_tts.log'),
            logging.StreamHandler()
        ]
    )

# === 進度指示器 ===
def show_progress(message: str, duration: float = 0.5, show_dots: bool = True):
    """顯示進度指示"""
    if app_config.skip_progress_indicators:
        print(f"⏳ {message}")
        return
    
    if show_dots:
        print(f"⏳ {message}", end="", flush=True)
        time.sleep(duration)
        print(" ✅")
    else:
        print(f"⏳ {message}")


def show_fast_progress(message: str):
    """快速進度指示（無延遲）"""
    print(f"⚡ {message}")


def show_progress_with_dots(message: str, total_steps: int = 3):
    """顯示帶點點的進度指示"""
    if app_config.skip_progress_indicators:
        print(f"⚡ {message}")
        return
    
    print(f"⏳ {message}", end="", flush=True)
    for i in range(total_steps):
        time.sleep(0.3)
        print(".", end="", flush=True)
    print(" ✅")


def show_loading_bar(message: str, duration: float = 2.0, width: int = 20):
    """顯示載入進度條"""
    print(f"⏳ {message}")
    for i in range(width + 1):
        progress = i / width
        bar = "█" * i + "░" * (width - i)
        print(f"\r[{bar}] {progress*100:.0f}%", end="", flush=True)
        time.sleep(duration / width)
    print()  # 換行

# === 記憶體優化 ===
def _optimize_audio_buffer(audio_buffer: list, max_frames: Optional[int] = None) -> list:
    """優化音訊緩衝區記憶體使用"""
    if max_frames is None:
        max_frames = app_config.audio.max_buffer_frames
    
    if len(audio_buffer) > max_frames:
        # 只保留最近的音訊幀，釋放舊的記憶體
        return audio_buffer[-max_frames:]
    return audio_buffer


def _cleanup_old_frames(audio_buffer: list, threshold: Optional[int] = None) -> list:
    """清理舊的音訊幀以釋放記憶體"""
    if threshold is None:
        threshold = app_config.audio.buffer_cleanup_threshold
    
    if len(audio_buffer) > threshold:
        # 保留最近的幀，清理舊的
        return audio_buffer[-threshold:]
    return audio_buffer


def _get_memory_usage() -> float:
    """獲取當前記憶體使用量（MB）"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # 轉換為 MB
    except ImportError:
        return 0.0


def _log_memory_usage(operation: str):
    """記錄記憶體使用情況（已停用）"""
    pass  # 不再輸出記憶體資訊

# === Rules loader & matcher ===
_RULES_CACHE = {"path": None, "mtime": 0.0, "data": None, "compiled_regex": {}}

# === 預載入回覆模板系統 ===
class ReplyTemplateCache:
    """回覆模板快取系統（支援持久化）"""
    
    def __init__(self):
        self.cache = {}  # {query_hash: {"reply": str, "timestamp": float, "count": int}}
        self.common_templates = {}  # 常用回覆模板
        self.prediction_queue = []  # 預測佇列
        self.last_save_time = time.time()  # 上次儲存時間
        self.rule_cache = {}  # 規則匹配結果快取
        self._load_common_templates()
        self._load_persistent_cache()
    
    def _load_common_templates(self):
        """載入常用回覆模板"""
        self.common_templates = {
            # 羽球相關常用回覆
            "開始": ["好的，我們開始練習吧！", "準備好了嗎？開始發球！", "開始訓練！"],
            "停止": ["好的，停止發球。", "訓練結束！", "停止發球機。"],
            "速度": ["調整發球速度", "速度設定完成", "發球速度已調整"],
            "角度": ["調整發球角度", "角度設定完成", "發球角度已調整"],
            "球數": ["剩餘球數", "球數統計", "發球數量"],
            "幫助": ["我可以幫你控制發球機", "需要什麼幫助嗎？", "有什麼問題嗎？"],
            "謝謝": ["不客氣！", "很高興能幫助你", "隨時為你服務"],
            "你好": ["你好！我是你的羽球發球機助理", "嗨！準備開始訓練嗎？", "你好！今天想練什麼？"],
            
            # 通用回覆
            "不知道": ["我不太確定，讓我再想想", "這個問題有點難，讓我查一下", "我需要更多資訊"],
            "重複": ["請再說一遍", "我沒聽清楚", "可以重複一次嗎？"],
            "確認": ["好的，我明白了", "收到！", "確認完成"],
            "取消": ["已取消", "操作取消", "取消完成"],
        }
    
    def cache_rule_result(self, query: str, rule_result: dict):
        """快取規則匹配結果"""
        if not (app_config.preload.enabled and app_config.preload.rule_cache_enabled):
            return
        
        query_hash = self._hash_query(query)
        self.rule_cache[query_hash] = {
            "rule": rule_result,
            "timestamp": time.time(),
            "count": 1
        }
    
    def get_cached_rule_result(self, query: str) -> Optional[dict]:
        """獲取快取的規則匹配結果"""
        if not (app_config.preload.enabled and app_config.preload.rule_cache_enabled):
            return None
        
        query_hash = self._hash_query(query)
        if query_hash in self.rule_cache:
            cached = self.rule_cache[query_hash]
            # 檢查快取是否過期
            if time.time() - cached["timestamp"] < app_config.preload.rule_cache_ttl:
                cached["count"] += 1
                return cached["rule"]
            else:
                # 過期則移除
                del self.rule_cache[query_hash]
        
        return None
    
    def _hash_query(self, query: str) -> str:
        """生成查詢的雜湊值"""
        import hashlib
        normalized = _normalize_zh(query)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get_cached_reply(self, query: str) -> Optional[str]:
        """獲取快取的回覆"""
        if not app_config.preload.enabled:
            return None
        
        query_hash = self._hash_query(query)
        if query_hash in self.cache:
            cached = self.cache[query_hash]
            # 檢查快取是否過期
            if time.time() - cached["timestamp"] < app_config.preload.cache_ttl:
                cached["count"] += 1
                return cached["reply"]
            else:
                # 過期則移除
                del self.cache[query_hash]
        
        return None
    
    
    def _cleanup_cache(self):
        """清理快取（移除最少使用的項目）"""
        if not self.cache:
            return
        
        # 按使用次數排序，移除最少使用的
        sorted_items = sorted(self.cache.items(), key=lambda x: x[1]["count"])
        # 移除最舊的 25%
        remove_count = max(1, len(sorted_items) // 4)
        for key, _ in sorted_items[:remove_count]:
            del self.cache[key]
    
    def predict_and_preload(self, current_query: str, conversation_history: list):
        """預測可能的後續問題並預載入"""
        if not app_config.preload.prediction_enabled:
            return
        
        # 基於當前查詢和對話歷史預測可能的後續問題
        predictions = self._generate_predictions(current_query, conversation_history)
        
        # 將預測加入佇列
        for prediction in predictions:
            if prediction not in self.prediction_queue:
                self.prediction_queue.append(prediction)
    
    def _generate_predictions(self, current_query: str, conversation_history: list) -> list:
        """生成預測查詢（基於規則系統）"""
        predictions = []
        
        # 基於關鍵詞預測
        query_lower = current_query.lower()
        
        # 羽球訓練相關預測
        if "開始" in query_lower or "start" in query_lower:
            predictions.extend(["停止", "快速", "慢速", "前場", "後場", "殺球"])
        elif "停止" in query_lower or "stop" in query_lower:
            predictions.extend(["開始", "狀態", "球數"])
        elif "速度" in query_lower or "speed" in query_lower or "快" in query_lower or "慢" in query_lower:
            predictions.extend(["角度", "開始", "停止", "左邊", "右邊"])
        elif "角度" in query_lower or "angle" in query_lower or "左" in query_lower or "右" in query_lower:
            predictions.extend(["速度", "開始", "停止", "提高", "降低"])
        elif "球數" in query_lower or "ball" in query_lower or "剩餘" in query_lower:
            predictions.extend(["開始", "停止", "狀態"])
        elif "前場" in query_lower or "網前" in query_lower:
            predictions.extend(["後場", "殺球", "吊球", "停止"])
        elif "後場" in query_lower or "底線" in query_lower:
            predictions.extend(["前場", "殺球", "吊球", "停止"])
        elif "殺球" in query_lower or "扣殺" in query_lower:
            predictions.extend(["吊球", "前場", "後場", "停止"])
        elif "吊球" in query_lower or "輕吊" in query_lower:
            predictions.extend(["殺球", "前場", "後場", "停止"])
        
        # 基於對話歷史預測
        if conversation_history:
            last_reply = conversation_history[-1].get("content", "").lower()
            if "開始" in last_reply:
                predictions.extend(["停止", "快速", "慢速", "前場", "後場"])
            elif "速度" in last_reply or "快" in last_reply or "慢" in last_reply:
                predictions.extend(["角度", "開始", "左邊", "右邊"])
            elif "角度" in last_reply or "左" in last_reply or "右" in last_reply:
                predictions.extend(["速度", "開始", "提高", "降低"])
        
        return predictions[:8]  # 增加預測數量
    
    def get_common_reply(self, query: str) -> Optional[str]:
        """獲取常用回覆模板"""
        query_lower = _normalize_zh(query)
        
        # 直接匹配
        for key, replies in self.common_templates.items():
            if key in query_lower:
                import random
                return random.choice(replies)
        
        # 模糊匹配
        for key, replies in self.common_templates.items():
            if fuzz.partial_ratio(query_lower, key) >= 80:
                import random
                return random.choice(replies)
        
        return None
    
    def _load_persistent_cache(self):
        """載入持久化快取"""
        if not app_config.preload.persistent_cache:
            return
        
        cache_file = app_config.preload.cache_file
        try:
            # 確保快取目錄存在
            cache_dir = os.path.dirname(cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 載入快取資料
                for query_hash, cache_data in data.get("cache", {}).items():
                    # 檢查快取是否過期
                    if time.time() - cache_data["timestamp"] < app_config.preload.cache_ttl:
                        self.cache[query_hash] = cache_data
                
                print(f"📂 載入持久化快取：{len(self.cache)} 個項目")
            else:
                print("📂 未找到快取檔案，將建立新的快取")
                
        except Exception as e:
            print(f"⚠️ 載入快取失敗：{e}")
    
    def _save_persistent_cache(self):
        """儲存持久化快取"""
        if not app_config.preload.persistent_cache:
            return
        
        cache_file = app_config.preload.cache_file
        try:
            # 確保快取目錄存在
            cache_dir = os.path.dirname(cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            
            # 準備儲存資料
            data = {
                "cache": self.cache,
                "metadata": {
                    "saved_at": time.time(),
                    "version": "1.0",
                    "total_items": len(self.cache)
                }
            }
            
            # 儲存到檔案
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.last_save_time = time.time()
            print(f"💾 快取已儲存：{len(self.cache)} 個項目")
            
        except Exception as e:
            print(f"⚠️ 儲存快取失敗：{e}")
    
    def _should_auto_save(self) -> bool:
        """檢查是否應該自動儲存"""
        return (time.time() - self.last_save_time) >= app_config.preload.auto_save_interval
    
    def cache_reply(self, query: str, reply: str):
        """快取回覆（支援自動儲存）"""
        if not app_config.preload.enabled:
            return
        
        query_hash = self._hash_query(query)
        
        # 檢查快取大小限制
        if len(self.cache) >= app_config.preload.max_cache_size:
            self._cleanup_cache()
        
        self.cache[query_hash] = {
            "reply": reply,
            "timestamp": time.time(),
            "count": 1
        }
        
        # 檢查是否需要自動儲存
        if self._should_auto_save():
            self._save_persistent_cache()
    
    def get_cache_stats(self) -> dict:
        """獲取快取統計資訊"""
        return {
            "cache_size": len(self.cache),
            "rule_cache_size": len(self.rule_cache),
            "common_templates": len(self.common_templates),
            "prediction_queue": len(self.prediction_queue),
            "total_queries": sum(item["count"] for item in self.cache.values()),
            "total_rule_hits": sum(item["count"] for item in self.rule_cache.values()),
            "persistent_cache": app_config.preload.persistent_cache,
            "cache_file": app_config.preload.cache_file,
            "last_save": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_save_time))
        }
    
    def save_cache_now(self):
        """立即儲存快取"""
        self._save_persistent_cache()
    
    def clear_cache(self):
        """清空快取"""
        self.cache.clear()
        self.rule_cache.clear()
        if app_config.preload.persistent_cache:
            self._save_persistent_cache()
        print("🗑️ 快取已清空")

# 全域快取實例
reply_cache = ReplyTemplateCache()

# === 模式管理系統 ===
class ModeManager:
    """模式管理器：處理控制模式和思考模式的切換"""
    
    def __init__(self, default_mode: str = "control", think_on: str = "啟動思考模式", 
                 control_on: str = "啟動控制模式", mismatch_reply: str = "我現在在控制模式，請用明確的指令再說一次。"):
        self.current_mode = default_mode  # "control" 或 "think"
        self.think_on_keyword = think_on
        self.control_on_keyword = control_on
        self.mismatch_reply = mismatch_reply
        self.mode_history = []  # 記錄模式切換歷史
        
    def get_current_mode(self) -> str:
        """獲取當前模式"""
        return self.current_mode
    
    def is_control_mode(self) -> bool:
        """檢查是否為控制模式"""
        return self.current_mode == "control"
    
    def is_think_mode(self) -> bool:
        """檢查是否為思考模式"""
        return self.current_mode == "think"
    
    def check_mode_switch(self, text: str) -> Optional[str]:
        """檢查是否觸發模式切換，返回切換後的回覆或 None"""
        normalized_text = _normalize_zh(text)
        think_keyword = _normalize_zh(self.think_on_keyword)
        control_keyword = _normalize_zh(self.control_on_keyword)
        
        # 檢查是否要切換到思考模式
        if think_keyword in normalized_text and self.current_mode == "control":
            self._switch_to_think()
            return f"已切換到思考模式，現在可以使用 LLM 進行對話。"
        
        # 檢查是否要切換到控制模式
        if control_keyword in normalized_text and self.current_mode == "think":
            self._switch_to_control()
            return f"已切換到控制模式，只使用規則匹配，不使用 LLM。"
        
        return None
    
    def _switch_to_think(self):
        """切換到思考模式"""
        old_mode = self.current_mode
        self.current_mode = "think"
        self.mode_history.append({
            "from": old_mode,
            "to": "think",
            "timestamp": time.time()
        })
        print(f"🔄 模式切換：{old_mode} → think")
    
    def _switch_to_control(self):
        """切換到控制模式"""
        old_mode = self.current_mode
        self.current_mode = "control"
        self.mode_history.append({
            "from": old_mode,
            "to": "control",
            "timestamp": time.time()
        })
        print(f"🔄 模式切換：{old_mode} → control")
    
    def get_mismatch_reply(self) -> str:
        """獲取控制模式下規則不匹配時的回覆"""
        return self.mismatch_reply
    
    def get_mode_status(self) -> dict:
        """獲取模式狀態資訊"""
        return {
            "current_mode": self.current_mode,
            "think_keyword": self.think_on_keyword,
            "control_keyword": self.control_on_keyword,
            "switch_count": len(self.mode_history),
            "last_switch": self.mode_history[-1] if self.mode_history else None
        }

class PreloadManager:
    """預載入管理器"""
    
    def __init__(self, client: OpenAI):
        self.client = client
        self.preload_thread = None
        self.is_running = False
        self.preload_queue = []
    
    def start_background_preload(self):
        """啟動背景預載入執行緒"""
        if not app_config.preload.enabled:
            return
        
        self.is_running = True
        self.preload_thread = threading.Thread(target=self._background_preload_worker, daemon=True)
        self.preload_thread.start()
        print("🔄 背景預載入執行緒已啟動")
    
    def stop_background_preload(self):
        """停止背景預載入執行緒"""
        self.is_running = False
        if self.preload_thread:
            self.preload_thread.join(timeout=1)
        print("⏹️ 背景預載入執行緒已停止")
    
    def _background_preload_worker(self):
        """背景預載入工作執行緒"""
        while self.is_running:
            try:
                # 處理預載入佇列
                if reply_cache.prediction_queue:
                    prediction = reply_cache.prediction_queue.pop(0)
                    self._preload_reply(prediction)
                
                # 處理預載入佇列
                if self.preload_queue:
                    query = self.preload_queue.pop(0)
                    self._preload_reply(query)
                
                time.sleep(0.1)  # 短暫休息
                
            except Exception as e:
                print(f"⚠️ 預載入執行緒錯誤：{e}")
                time.sleep(1)
    
    def _preload_reply(self, query: str):
        """預載入回覆"""
        try:
            # 檢查是否已經快取
            if reply_cache.get_cached_reply(query):
                return
            
            # 首先檢查規則匹配
            rule_result = self._preload_rule_match(query)
            if rule_result:
                return
            
            # 檢查是否有常用回覆模板
            common_reply = reply_cache.get_common_reply(query)
            if common_reply:
                reply_cache.cache_reply(query, common_reply)
                return
            
            # 使用 LLM 生成回覆（低優先級）
            if len(reply_cache.cache) < app_config.preload.max_cache_size // 2:
                reply = self._generate_preload_reply(query)
                if reply:
                    reply_cache.cache_reply(query, reply)
        
        except Exception as e:
            print(f"⚠️ 預載入回覆失敗：{e}")
    
    def _preload_rule_match(self, query: str) -> bool:
        """預載入規則匹配結果"""
        if not app_config.preload.preload_rules:
            return False
            
        try:
            # 使用預設規則檔案進行匹配
            default_rules_path = "rules/badminton_rules.yaml"
            if os.path.exists(default_rules_path):
                matcher = RuleMatcher(default_rules_path)
                hit = matcher.match(query)
                if hit:
                    # 快取規則匹配結果
                    reply_cache.cache_rule_result(query, hit)
                    
                    # 生成並快取回覆
                    context = {"balls_left": 48}
                    reply_text = format_reply(hit.get("reply", {}).get("text", ""), context)
                    reply_cache.cache_reply(query, reply_text)
                    return True
        except Exception as e:
            print(f"⚠️ 預載入規則匹配失敗：{e}")
        
        return False
    
    def _generate_preload_reply(self, query: str) -> Optional[str]:
        """生成預載入回覆"""
        try:
            # 使用簡潔的系統提示
            system_prompt = "你是羽球發球機助理，請用簡潔的1-2句話回覆。"
            
            reply = llm_reply(
                self.client,
                query,
                system_prompt,
                temperature=0.3,  # 較低溫度確保一致性
                max_tokens=50,    # 限制長度
                conversation_history=None
            )
            return reply
        
        except Exception as e:
            print(f"⚠️ 生成預載入回覆失敗：{e}")
            return None
    
    def add_to_preload_queue(self, query: str):
        """添加查詢到預載入佇列"""
        if query not in self.preload_queue:
            self.preload_queue.append(query)
    
    def preload_common_queries(self):
        """預載入常用查詢（基於規則系統）"""
        common_queries = [
            # 基本控制
            "開始發球", "停止發球", "開始訓練", "停止訓練",
            # 速度控制
            "快速", "慢速", "中速", "加速", "減速",
            # 角度控制
            "左邊", "右邊", "中間", "左轉", "右轉",
            # 高度控制
            "提高", "降低", "上升", "下降",
            # 訓練模式
            "前場練習", "後場練習", "殺球練習", "吊球練習",
            "正手練習", "反手練習", "直線球", "斜線球",
            # 狀態查詢
            "剩餘球數", "現在狀態", "進度如何", "報告狀態",
            # 基本互動
            "幫助", "謝謝", "你好", "再見", "辛苦了"
        ]
        
        for query in common_queries:
            self.add_to_preload_queue(query)
        
        print(f"📋 已排程 {len(common_queries)} 個常用查詢預載入")

class RuleMatcher:
    """優化的規則匹配器，支援預編譯和快取"""
    
    def __init__(self, rules_path: str):
        self.rules_path = rules_path
        self._compiled_regex = {}
        self._rules_data = None
        self._last_mtime = 0.0
        self._cache_enabled = True
    
    def _load_rules(self) -> dict:
        """載入規則並預編譯正則表達式"""
        global _RULES_CACHE
        p = os.path.abspath(self.rules_path)
        mtime = os.path.getmtime(p)
        
        # 檢查快取
        if (_RULES_CACHE["path"] == p and 
            _RULES_CACHE["mtime"] == mtime and 
            _RULES_CACHE["data"] is not None):
            return _RULES_CACHE["data"]
        
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        # 預處理和預編譯
        for r in data.get("rules", []):
            r.setdefault("priority", 0)
            r.setdefault("match", {})
            r["match"].setdefault("contains", [])
            r["match"].setdefault("regex", [])
            r["match"].setdefault("fuzzy", [])
            
            # 預建正規化字串以加速
            r["_contains_norm"] = [_normalize_zh(x) for x in r["match"]["contains"]]
            
            # 預編譯正則表達式
            r["_compiled_regex"] = self._compile_regex(r["match"]["regex"])
        
        # 更新快取
        _RULES_CACHE = {
            "path": p, 
            "mtime": mtime, 
            "data": data,
            "compiled_regex": {}
        }
        
        return data
    
    def _compile_regex(self, patterns: list) -> list:
        """預編譯正則表達式"""
        compiled = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern))
            except re.error as e:
                print(f"⚠️ 無效的正則表達式：{pattern} - {e}")
        return compiled
    
    def match(self, text: str) -> Optional[dict]:
        """匹配規則（支援快取）"""
        if not text.strip():
            return None
        
        # 首先檢查快取
        if self._cache_enabled:
            cached_result = reply_cache.get_cached_rule_result(text)
            if cached_result:
                print("⚡ 使用規則快取結果")
                return cached_result
        
        rules_data = self._load_rules()
        ntext = _normalize_zh(text)
        rules = sorted(rules_data.get("rules", []), 
                      key=lambda r: r.get("priority", 0), reverse=True)
        fuzzy_th = rules_data.get("globals", {}).get("fuzzy_threshold", 86)

        for r in rules:
            # 1) 包含式（正規化）
            for key_norm in r.get("_contains_norm", []):
                if key_norm and key_norm in ntext:
                    # 快取結果
                    if self._cache_enabled:
                        reply_cache.cache_rule_result(text, r)
                    return r
            
            # 2) 正則（使用預編譯）
            for compiled_regex in r.get("_compiled_regex", []):
                if compiled_regex.search(text):
                    # 快取結果
                    if self._cache_enabled:
                        reply_cache.cache_rule_result(text, r)
                    return r
            
            # 3) 模糊比對（對正規化後字串）
            for k in r["match"].get("fuzzy", []):
                if fuzz.partial_ratio(ntext, _normalize_zh(k)) >= fuzzy_th:
                    # 快取結果
                    if self._cache_enabled:
                        reply_cache.cache_rule_result(text, r)
                    return r
        
        return None

# === Wake word config ===
DEFAULT_WAKE = "啟動語音發球機"
DEFAULT_WAKE_REPLY = "彥澤您好，我是你的智慧羽球發球機助理，今天想練什麼呢？"

_ZH_PUNCT = "，。！？、；：「」『』（）【】《》—．…‧,.!?;:()[]{}<>~`@#$%^&*-_=+|/\\\"'\u3000 "  # 含全形空白

def _normalize_zh(s: str) -> str:
    s = (s or "").strip().lower()
    for ch in _ZH_PUNCT:
        s = s.replace(ch, "")
    return s

def is_wake_hit(text: str, wake: str) -> bool:
    """移除空白/標點，比對是否包含喚醒詞（容忍有空格或標點）。"""
    return _normalize_zh(wake) in _normalize_zh(text)


def load_rules(path: str) -> dict:
    """含簡易快取；若規則檔 mtime 變動才重讀。"""
    global _RULES_CACHE
    p = os.path.abspath(path)
    mtime = os.path.getmtime(p)
    if _RULES_CACHE["path"] == p and _RULES_CACHE["mtime"] == mtime and _RULES_CACHE["data"] is not None:
        return _RULES_CACHE["data"]

    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # 預處理：priority 預設、欄位容錯
    for r in data.get("rules", []):
        r.setdefault("priority", 0)
        r.setdefault("match", {})
        r["match"].setdefault("contains", [])
        r["match"].setdefault("regex", [])
        r["match"].setdefault("fuzzy", [])
        # 預建正規化字串以加速
        r["_contains_norm"] = [_normalize_zh(x) for x in r["match"]["contains"]]
    _RULES_CACHE = {"path": p, "mtime": mtime, "data": data}
    return data

def match_rules(text: str, rules_data: dict) -> Optional[dict]:
    """回傳第一個命中的規則（依 priority 由高到低）。"""
    if not text.strip():
        return None
    ntext = _normalize_zh(text)
    rules = sorted(rules_data.get("rules", []), key=lambda r: r.get("priority", 0), reverse=True)
    fuzzy_th = rules_data.get("globals", {}).get("fuzzy_threshold", 86)

    for r in rules:
        # 1) 包含式（正規化）
        for key_norm in r.get("_contains_norm", []):
            if key_norm and key_norm in ntext:
                return r
        # 2) 正則（用原文）
        for pat in r["match"].get("regex", []):
            try:
                if re.search(pat, text):
                    return r
            except re.error:
                continue
        # 3) 模糊比對（對正規化後字串）
        for k in r["match"].get("fuzzy", []):
            if fuzz.partial_ratio(ntext, _normalize_zh(k)) >= fuzzy_th:
                return r
    return None

def format_reply(template: str, context: dict) -> str:
    try:
        return template.format(**context)
    except Exception:
        return template  # 缺少變數就用原樣


def list_avfoundation_devices() -> None:
    """列出 avfoundation 輸入裝置（macOS）。"""
    if shutil.which("ffmpeg") is None:
        print("找不到 ffmpeg，請先安裝：brew install ffmpeg")
        return
    # 列出裝置
    subprocess.run(["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""], check=False)


def list_sd_input_devices() -> None:
    """列出 sounddevice 可用輸入裝置。"""
    import sounddevice as sd  # 延後匯入，避免未安裝時影響其它功能
    print("=== 可用錄音裝置（sounddevice input devices）===")
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0:
            mark = " (預設)" if sd.default.device and i == sd.default.device[0] else ""
            print(f"[{i}] {d.get('name','?')}  max_in={d.get('max_input_channels',0)}{mark}")


def record_wav_ffmpeg(seconds: int, out_path: str, adev: int = 0) -> None:
    """以 ffmpeg（avfoundation）在 macOS 錄音作為備援。
    需安裝 ffmpeg：brew install ffmpeg
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("找不到 ffmpeg，請先安裝：brew install ffmpeg")
    # 使用預設麥克風（:0），16k/單聲道/16-bit PCM
    cmd = [
        "ffmpeg", "-y",
        "-f", "avfoundation", "-i", f":{adev}",
        "-t", str(seconds),
        "-ac", str(CHANNELS),
        "-ar", str(SAMPLE_RATE),
        "-acodec", "pcm_s16le",
        out_path,
    ]
    print(f"🎙️ ffmpeg 備援錄音 {seconds} 秒（adev={adev}）...")
    subprocess.run(cmd, check=True)
    print(f"✅ 已儲存（ffmpeg）：{out_path}")


def record_wav(seconds: int, out_path: str, adev: int = 0, sd_device: Optional[int] = None) -> None:
    print(f"🎙️ 開始錄音 {seconds} 秒...")
    try:
        # 優先嘗試 sounddevice 錄音
        if sd_device is not None:
            sd.default.device = (sd_device, None)  # (input, output)
        sd.default.samplerate = SAMPLE_RATE
        sd.default.channels = CHANNELS
        audio = sd.rec(int(seconds * SAMPLE_RATE), dtype="int16")
        sd.wait()
        wavwrite(out_path, SAMPLE_RATE, audio)
        print(f"✅ 已儲存：{out_path}")
    except MemoryError as e:
        print("⚠️ sounddevice/cffi 記憶體限制，改用 ffmpeg 備援。", e)
        record_wav_ffmpeg(seconds, out_path, adev=adev)
    except Exception as e:
        print("⚠️ sounddevice 錄音失敗，改用 ffmpeg 備援。", e)
        record_wav_ffmpeg(seconds, out_path, adev=adev)


def _record_with_vad_common(out_path: str, aggressiveness: Optional[int] = None, 
                           silence_ms: Optional[int] = None, sd_device: Optional[int] = None, 
                           realtime_transcribe: bool = False, low_latency: bool = False) -> str:
    """VAD 錄音的共通邏輯"""
    if not WEBRTCVAD_AVAILABLE:
        raise RuntimeError("webrtcvad 未安裝，請執行：pip install webrtcvad")
    
    if realtime_transcribe:
        print("⚠️ 不支援即時轉錄，將在錄音完成後進行轉錄")
        realtime_transcribe = False
    
    # 使用配置中的預設值，支援低延遲模式
    if aggressiveness is None:
        aggressiveness = app_config.audio.aggressiveness
    if silence_ms is None:
        if low_latency:
            silence_ms = app_config.audio.ultra_fast_silence_ms
        else:
            silence_ms = app_config.audio.silence_ms
    
    print(f"🎙️ 開始錄音（VAD 模式），停頓 >{silence_ms/1000:.1f} 秒自動結束…")
    
    # 設定 VAD
    vad = webrtcvad.Vad(aggressiveness)
    
    # 錄音參數（使用配置）
    frame_duration_ms = app_config.audio.frame_duration_ms
    frame_size = int(app_config.audio.sample_rate * frame_duration_ms / 1000)
    silence_frames = int(silence_ms / frame_duration_ms)
    
    # 設定 sounddevice
    if sd_device is not None:
        sd.default.device = (sd_device, None)
    sd.default.samplerate = app_config.audio.sample_rate
    sd.default.channels = app_config.audio.channels
    
    # 開始錄音
    audio_buffer = []
    consecutive_silence = 0
    has_speech = False
    speech_frames = 0
    # 低延遲模式使用更少的語音幀要求
    min_speech_frames = app_config.audio.min_speech_frames_fast if low_latency else app_config.audio.min_speech_frames
    
    # _log_memory_usage("錄音開始前")  # 已停用記憶體記錄
    
    try:
        with sd.InputStream(samplerate=app_config.audio.sample_rate, 
                          channels=app_config.audio.channels, 
                          dtype="int16", blocksize=frame_size) as stream:
            while True:
                # 讀取一幀音訊
                audio_frame, overflowed = stream.read(frame_size)
                if overflowed:
                    print("⚠️ 音訊緩衝區溢出")
                
                # 轉換為 bytes 供 VAD 使用
                frame_bytes = audio_frame.tobytes()
                
                # VAD 偵測
                is_speech = vad.is_speech(frame_bytes, app_config.audio.sample_rate)
                
                if is_speech:
                    consecutive_silence = 0
                    has_speech = True
                    speech_frames += 1
                else:
                    consecutive_silence += 1
                
                # 儲存音訊幀
                audio_buffer.append(audio_frame)
                
                # 記憶體優化：定期清理舊幀
                if len(audio_buffer) % 100 == 0:  # 每 100 幀檢查一次
                    audio_buffer = _cleanup_old_frames(audio_buffer)
                
                # 檢查是否應該停止
                if has_speech and speech_frames >= min_speech_frames and consecutive_silence >= silence_frames:
                    print("\n🔇 偵測到靜音，停止錄音")
                    break
                
                # 防止錄音過長
                if len(audio_buffer) * frame_duration_ms > app_config.audio.max_recording_ms:
                    print("\n⏰ 錄音時間過長，自動停止")
                    break
    
    except Exception as e:
        print(f"\n⚠️ VAD 錄音失敗：{e}")
        raise
    
    # 合併音訊並儲存
    if audio_buffer:
        # 最終記憶體優化
        audio_buffer = _optimize_audio_buffer(audio_buffer)
        # _log_memory_usage("音訊處理前")  # 已停用記憶體記錄
        
        full_audio = np.concatenate(audio_buffer, axis=0)
        wavwrite(out_path, app_config.audio.sample_rate, full_audio)
        
        # 清理記憶體
        del audio_buffer
        del full_audio
        
        # _log_memory_usage("音訊處理後")  # 已停用記憶體記錄
        print(f"✅ 已存檔 {out_path}")
    else:
        print("⚠️ 沒有錄到任何音訊")
        # 建立一個空的 wav 檔案
        empty_audio = np.zeros(int(app_config.audio.sample_rate * 0.1), dtype="int16")
        wavwrite(out_path, app_config.audio.sample_rate, empty_audio)
        del empty_audio
    
    return ""  # 不支援即時轉錄，返回空字串


def record_until_silence_realtime(out_path: str = "input.wav", aggressiveness: int = 2, silence_ms: int = 300, sd_device: Optional[int] = None, realtime_transcribe: bool = False) -> str:
    """使用 webrtcvad 偵測語音活動，自動停止錄音，可選即時轉錄"""
    return _record_with_vad_common(out_path, aggressiveness, silence_ms, sd_device, realtime_transcribe)


def record_until_silence(out_path: str = "input.wav", aggressiveness: int = 2, silence_ms: int = 300, sd_device: Optional[int] = None, low_latency: bool = False) -> None:
    """使用 webrtcvad 偵測語音活動，自動停止錄音"""
    _record_with_vad_common(out_path, aggressiveness, silence_ms, sd_device, low_latency=low_latency)


def s2twp(text: str, enabled: bool = True) -> str:
    if not enabled or not text:
        return text
    if _cc is None:
        print("ℹ️ 建議安裝 opencc-python-reimplemented 以輸出繁體：pip install opencc-python-reimplemented")
        return text
    return _cc.convert(text)


def asr_transcribe_whisper(client: OpenAI, wav_path: str, language: str = "zh", model: str = "whisper-1") -> str:
    """使用 Whisper API 進行語音識別"""
    if not os.path.exists(wav_path):
        raise RuntimeError(f"音訊檔案不存在：{wav_path}")
    
    print(f"🧠 語音轉錄中... (語言: {language}, 模型: {model})")
    
    try:
        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                response_format="text"
            )
        
        # 清理轉錄結果
        text = transcript.strip() if isinstance(transcript, str) else str(transcript).strip()
        return text
        
    except Exception as e:
        print(f"❌ 語音轉錄失敗：{e}")
        return ""


def asr_transcribe_whisper_with_retry(client: OpenAI, wav_path: str, language: str = "zh", 
                                    model: str = "whisper-1", max_retries: Optional[int] = None) -> str:
    """帶重試機制的語音轉錄"""
    if max_retries is None:
        max_retries = app_config.max_retries
    
    for attempt in range(max_retries):
        try:
            result = asr_transcribe_whisper(client, wav_path, language, model)
            if result:  # 如果成功取得結果
                return result
            elif attempt < max_retries - 1:  # 如果結果為空但不是最後一次嘗試
                print(f"⚠️ 轉錄結果為空，重試中... ({attempt + 1}/{max_retries})")
                time.sleep(app_config.retry_delay)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ 轉錄最終失敗：{e}")
                raise
            print(f"⚠️ 轉錄失敗，重試中... ({attempt + 1}/{max_retries}): {e}")
            time.sleep(app_config.retry_delay)
    
    return ""


def llm_reply_with_retry(client: OpenAI, user_text: str, system_prompt: Optional[str], 
                        *, temperature: float, max_tokens: int, 
                        conversation_history: Optional[list] = None,
                        max_retries: Optional[int] = None) -> str:
    """帶重試機制的 LLM 回覆"""
    if max_retries is None:
        max_retries = app_config.max_retries
    
    for attempt in range(max_retries):
        try:
            return llm_reply(client, user_text, system_prompt, 
                           temperature=temperature, max_tokens=max_tokens,
                           conversation_history=conversation_history)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ LLM 回覆最終失敗：{e}")
                raise
            print(f"⚠️ LLM 回覆失敗，重試中... ({attempt + 1}/{max_retries}): {e}")
            time.sleep(app_config.retry_delay)
    
    return ""


def tts_speak_with_retry(client: OpenAI, text: str, voice: str, output_path: str, 
                        speed_factor: float = 1.0, max_retries: Optional[int] = None) -> None:
    """帶重試機制的 TTS 語音合成"""
    if max_retries is None:
        max_retries = app_config.max_retries
    
    for attempt in range(max_retries):
        try:
            tts_speak(client, text, voice, output_path, speed_factor)
            return  # 成功則直接返回
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ TTS 合成最終失敗：{e}")
                raise
            print(f"⚠️ TTS 合成失敗，重試中... ({attempt + 1}/{max_retries}): {e}")
            time.sleep(app_config.retry_delay)


def _parallel_api_calls(client: OpenAI, asr_text: str, args: argparse.Namespace, 
                       conversation_history: Optional[list]) -> tuple[str, str]:
    """並行執行 LLM 和 TTS 調用以降低延遲"""
    if not app_config.parallel_processing:
        # 如果不啟用並行處理，使用原有順序
        reply = llm_reply_with_retry(
            client, asr_text, args.system,
            temperature=args.temperature, max_tokens=args.max_tokens,
            conversation_history=conversation_history
        )
        return reply, ""
    
    # 並行處理：同時準備 LLM 和預先載入 TTS
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # 提交 LLM 任務
        llm_future = executor.submit(
            llm_reply_with_retry,
            client, asr_text, args.system,
            temperature=args.temperature, max_tokens=args.max_tokens,
            conversation_history=conversation_history
        )
        
        # 等待 LLM 完成
        reply = llm_future.result()
        
        # 立即返回結果，TTS 在後台處理
        return reply, ""


def _streaming_tts(client: OpenAI, text: str, voice: str, output_path: str, 
                  speed_factor: float = 1.0) -> None:
    """流式 TTS 處理（在後台執行）"""
    try:
        tts_speak_with_retry(client, text, voice, output_path, speed_factor)
        print(f"✅ 背景 TTS 完成：{output_path}")
    except Exception as e:
        print(f"❌ 背景 TTS 失敗：{e}")


def llm_reply(client: OpenAI, user_text: str, system_prompt: Optional[str], *, temperature: float, max_tokens: int, conversation_history: Optional[list] = None) -> str:
    # 以繁體回覆，保留口語化語氣；若提供 system_prompt，加入對話風格指示
    messages = []
    
    # 添加系統提示
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 添加對話歷史（如果有的話）
    if conversation_history:
        messages.extend(conversation_history)
    
    # 添加當前用戶輸入
    messages.append({"role": "user", "content": user_text})
    
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def adjust_speed(input_path: str, output_path: str, speed_factor: float) -> None:
    """調整音訊播放速度"""
    if not PYDUB_AVAILABLE:
        print("⚠️ 無法調整語速：未安裝 pydub")
        return
    
    try:
        # 載入音訊檔案
        audio = AudioSegment.from_mp3(input_path)
        
        # 調整語速
        if speed_factor != 1.0:
            # 使用 pydub 的 speedup 效果
            audio = speedup(audio, playback_speed=speed_factor)
        
        # 儲存調整後的音訊
        audio.export(output_path, format="mp3")
        print(f"✅ 已調整語速至 {speed_factor}x 倍速")
        
    except Exception as e:
        print(f"❌ 語速調整失敗：{e}")


def tts_speak(client: OpenAI, text: str, voice: str, output_path: str, speed_factor: float = 1.0) -> None:
    if not text:
        raise ValueError("TTS 輸入文字為空。")
    
    # 如果不需要調整語速，直接輸出
    if speed_factor == 1.0:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
        )
        response.stream_to_file(output_path)
    else:
        # 需要調整語速時，先產生暫存檔案
        temp_output = f"temp_{output_path}"
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
        )
        response.stream_to_file(temp_output)
        
        # 調整語速
        adjust_speed(temp_output, output_path, speed_factor)
        
        # 刪除暫存檔案
        if os.path.exists(temp_output):
            os.remove(temp_output)


def autoplay_mac(path: str, enabled: bool = True) -> None:
    if not enabled:
        return
    try:
        subprocess.run(["afplay", path], check=False)
    except Exception:
        pass


def _prepare_audio_input(args: argparse.Namespace) -> tuple[str, str]:
    """準備音訊輸入，返回 (wav_path, asr_text)"""
    wav_path = args.input
    asr_text = ""
    
    if not wav_path:
        tmp_path = pathlib.Path(args.tmp or "input.wav").as_posix()
        if args.realtime:
            # 即時轉錄模式：錄音同時即時轉錄
            asr_text = record_until_silence_realtime(tmp_path, sd_device=args.sd_device, realtime_transcribe=True)
            wav_path = tmp_path
        elif args.duration is not None:
            # 傳統模式：固定秒數錄音
            record_wav(args.duration, tmp_path, adev=args.adev, sd_device=args.sd_device)
            wav_path = tmp_path
        else:
            # 預設 VAD 模式：自動偵測語音結束（支援低延遲）
            low_latency = app_config.low_latency_mode
            record_until_silence(tmp_path, sd_device=args.sd_device, low_latency=low_latency)
            wav_path = tmp_path
    
    return wav_path, asr_text


def _process_asr(client: OpenAI, wav_path: str, asr_text: str, args: argparse.Namespace) -> str:
    """處理語音識別"""
    # ASR (使用 Whisper API)
    if not args.realtime or not asr_text:
        show_progress_with_dots("🧠 語音轉錄中", 3)
        asr_text = asr_transcribe_whisper_with_retry(client, wav_path, args.whisper_language, args.whisper_model)
    
    show_progress("🔄 轉換為繁體中文", 0.3)
    asr_text_trad = s2twp(asr_text, enabled=not args.no_s2twp)
    print("\n==== 轉錄結果 ====")
    print(asr_text_trad.strip())
    print("==================\n")
    
    return asr_text_trad


def _handle_rules_matching(asr_text_trad: str, args: argparse.Namespace, mode_manager: Optional['ModeManager'] = None) -> Optional[tuple[str, str]]:
    """處理規則匹配，返回 (reply_text, voice) 或 None"""
    if not (args.rules and not args.no_rules and RULES_AVAILABLE):
        if args.rules and not RULES_AVAILABLE:
            print("⚠️ 規則系統依賴未安裝，請執行：pip install pyyaml rapidfuzz")
        return None
    
    if app_config.low_latency_mode:
        show_fast_progress("🔍 檢查規則匹配")
    else:
        show_progress("🔍 檢查規則匹配", 0.2)
    
    try:
        # 使用優化的 RuleMatcher
        matcher = RuleMatcher(args.rules)
        hit = matcher.match(asr_text_trad)
        
        if not hit:
            # 如果沒有命中規則，且處於控制模式，返回固定引導語
            if mode_manager and mode_manager.is_control_mode():
                reply_text = mode_manager.get_mismatch_reply()
                print("⚠️ 控制模式下規則未命中，使用固定引導語")
                print("\n==== 固定引導語 ====")
                print(reply_text)
                print("==================\n")
                return reply_text, args.voice
            return None
        
        # 載入規則資料以取得全域設定
        rules_data = load_rules(args.rules)
        
    except Exception as e:
        print("⚠️ 規則檔讀取/比對失敗：", e)
        return None
    
    if app_config.low_latency_mode:
        show_fast_progress("⚙️ 處理規則回覆")
    else:
        show_progress("⚙️ 處理規則回覆", 0.3)
    
    # 可注入動態 context（例：剩餘球數、目前速度等）
    context = {
        "balls_left": 48,    # ← 這裡接到你的系統狀態
        # "speed": current_speed,
    }
    reply_text = format_reply(hit.get("reply", {}).get("text", ""), context)
    voice = hit.get("reply", {}).get("voice", rules_data.get("globals", {}).get("default_voice", args.voice)) or args.voice

    print(f"✅ 命中規則：{hit.get('id','(no-id)')}  action={hit.get('action','')}")
    print("\n==== 固定回覆 ====")
    print(reply_text)
    print("==================\n")

    # 快取規則回覆結果
    if app_config.preload.enabled:
        reply_cache.cache_reply(asr_text_trad, reply_text)

    # 這裡可對接你的實體動作（發球機 API）
    # do_action(hit.get("action"), context)
    
    return reply_text, voice


def _handle_wake_word(asr_text_trad: str, args: argparse.Namespace) -> Optional[str]:
    """處理喚醒詞，返回回覆文字或 None"""
    if not is_wake_hit(asr_text_trad, args.wake):
        return None
    
    reply_text = args.wake_reply
    print(f"🔔 喚醒詞命中：{args.wake} → 直接回覆")
    print("\n==== 固定回覆 ====")
    print(reply_text)
    print("==================\n")
    
    return reply_text


def _handle_llm_response(client: OpenAI, asr_text_trad: str, args: argparse.Namespace, 
                        conversation_history: Optional[list], preload_manager: Optional[PreloadManager] = None,
                        mode_manager: Optional['ModeManager'] = None) -> str:
    """處理 LLM 回應（支援預載入快取和模式分流）"""
    
    # 檢查是否處於控制模式，如果是則不應該進入 LLM 處理
    if mode_manager and mode_manager.is_control_mode():
        print("⚠️ 控制模式下不應進入 LLM 處理，這表示邏輯有誤")
        return mode_manager.get_mismatch_reply()
    
    # 首先檢查快取
    cached_reply = reply_cache.get_cached_reply(asr_text_trad)
    if cached_reply:
        print("⚡ 使用快取回覆")
        print("\n==== 快取回覆（文字）====")
        print(cached_reply)
        print("=======================\n")
        
        # 預測後續可能的問題
        if preload_manager:
            reply_cache.predict_and_preload(asr_text_trad, conversation_history or [])
        
        return cached_reply
    
    # 檢查常用回覆模板
    common_reply = reply_cache.get_common_reply(asr_text_trad)
    if common_reply:
        print("📋 使用常用回覆模板")
        print("\n==== 模板回覆（文字）====")
        print(common_reply)
        print("=======================\n")
        
        # 快取這個回覆
        reply_cache.cache_reply(asr_text_trad, common_reply)
        
        # 預測後續可能的問題
        if preload_manager:
            reply_cache.predict_and_preload(asr_text_trad, conversation_history or [])
        
        return common_reply
    
    # 使用 LLM 生成新回覆
    if app_config.low_latency_mode:
        show_fast_progress("🤖 準備 LLM 請求")
    else:
        show_progress("🤖 準備 LLM 請求", 0.2)
    
    # 若啟用簡潔模式，自動在 system 指示加入限制字數/句數與口吻
    system_prompt = args.system
    if args.concise:
        concise_rule = (
            "請用最短的方式回答， 1~2 句或 20 字以內"
            "幽默一點不要太正經，像個大學生聊天"
            "- 直入重點，避免贅述與列點。"
        )
        system_prompt = (system_prompt + "\n" + concise_rule).strip() if system_prompt else concise_rule

    if app_config.low_latency_mode:
        show_fast_progress("🧠 生成 LLM 回覆")
    else:
        show_progress_with_dots("🧠 生成 LLM 回覆", 4)
    
    reply = llm_reply_with_retry(
        client,
        asr_text_trad,
        system_prompt,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        conversation_history=conversation_history,
    )
    
    # 快取新生成的回覆
    reply_cache.cache_reply(asr_text_trad, reply)
    
    # 預測後續可能的問題
    if preload_manager:
        reply_cache.predict_and_preload(asr_text_trad, conversation_history or [])
    
    print("\n==== LLM 回覆（文字）====")
    print(reply)
    print("=======================\n")
    
    return reply


def _handle_tts_output(client: OpenAI, reply_text: str, voice: str, args: argparse.Namespace) -> None:
    """處理 TTS 輸出"""
    if app_config.low_latency_mode:
        show_fast_progress(f"🔊 轉為語音中 (語速: {args.speed}x)")
    else:
        show_progress_with_dots(f"🔊 轉為語音中 (語速: {args.speed}x)", 3)
    
    tts_speak_with_retry(client, reply_text, voice, args.output, args.speed)
    print(f"✅ 已產生語音檔：{args.output}")


def _update_conversation_history(conversation_history: Optional[list], 
                                asr_text_trad: str, reply: str) -> list:
    """更新對話歷史"""
    updated_history = conversation_history or []
    updated_history.append({"role": "user", "content": asr_text_trad})
    updated_history.append({"role": "assistant", "content": reply})
    
    # 限制對話歷史長度（保留最近 N 輪對話）
    max_history = app_config.max_conversation_history * 2  # 每輪對話 = 2 條訊息
    if len(updated_history) > max_history:
        updated_history = updated_history[-max_history:]
    
    return updated_history


def run_once(args: argparse.Namespace, client: OpenAI, conversation_history: Optional[list] = None, 
             preload_manager: Optional[PreloadManager] = None, mode_manager: Optional['ModeManager'] = None) -> tuple[str, list]:
    """主要執行流程，協調各個子函數（支援模式分流）"""
    # _log_memory_usage("流程開始")  # 已停用記憶體記錄
    
    # 1) 準備輸入音檔
    wav_path, asr_text = _prepare_audio_input(args)
    # _log_memory_usage("音訊準備完成")  # 已停用記憶體記錄

    # 2) 處理語音識別
    asr_text_trad = _process_asr(client, wav_path, asr_text, args)
    # _log_memory_usage("語音識別完成")  # 已停用記憶體記錄

    # 空輸入就不繼續
    if not asr_text_trad.strip():
        print("⚠️ 無內容，略過 LLM 與 TTS。")
        return "", conversation_history or []

    # 2.5) 檢查模式切換（優先處理）
    if mode_manager:
        mode_switch_reply = mode_manager.check_mode_switch(asr_text_trad)
        if mode_switch_reply:
            _handle_tts_output(client, mode_switch_reply, args.voice, args)
            autoplay_mac(args.output, enabled=not args.no_play)
            print(f"🔄 當前模式：{mode_manager.get_current_mode()}")
            return mode_switch_reply, conversation_history or []

    # 3) 規則匹配（支援模式分流）
    rules_result = _handle_rules_matching(asr_text_trad, args, mode_manager)
    if rules_result:
        reply_text, voice = rules_result
        _handle_tts_output(client, reply_text, voice, args)
        autoplay_mac(args.output, enabled=not args.no_play)
        # _log_memory_usage("規則匹配完成")  # 已停用記憶體記錄
        return reply_text, conversation_history or []

    # 4) 喚醒詞處理
    wake_reply = _handle_wake_word(asr_text_trad, args)
    if wake_reply:
        _handle_tts_output(client, wake_reply, args.voice, args)
        autoplay_mac(args.output, enabled=not args.no_play)
        # _log_memory_usage("喚醒詞處理完成")  # 已停用記憶體記錄
        return wake_reply, conversation_history or []

    # 5) LLM 回覆（支援預載入和模式分流）
    # 只有在思考模式下才使用 LLM
    if mode_manager and mode_manager.is_control_mode():
        # 控制模式下不應該到達這裡，因為規則匹配應該已經處理了
        print("⚠️ 控制模式下不應進入 LLM 處理，使用固定引導語")
        reply = mode_manager.get_mismatch_reply()
    else:
        reply = _handle_llm_response(client, asr_text_trad, args, conversation_history, preload_manager, mode_manager)
    # _log_memory_usage("LLM 回覆完成")  # 已停用記憶體記錄

    # 6) TTS 輸出
    _handle_tts_output(client, reply, args.voice, args)
    # _log_memory_usage("TTS 輸出完成")  # 已停用記憶體記錄

    # 7) 自動播放
    autoplay_mac(args.output, enabled=not args.no_play)
    
    # 8) 更新對話歷史
    updated_history = _update_conversation_history(conversation_history, asr_text_trad, reply)
    # _log_memory_usage("流程完成")  # 已停用記憶體記錄
    
    return reply, updated_history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="🏸 羽球發球機語音控制系統")
    g_in = parser.add_mutually_exclusive_group()
    g_in.add_argument("-d", "--duration", type=int, default=None, help="錄音秒數（與 -i 和 --vad 互斥）")
    g_in.add_argument("-i", "--input", type=str, default=None, help="輸入音檔路徑（.wav/.mp3/.m4a 等）")
    g_in.add_argument("--vad", action="store_true", default=True, help="啟用 VAD 模式，自動偵測語音結束（與 -d 和 -i 互斥）")
    g_in.add_argument("--realtime", action="store_true", help="啟用即時轉錄模式（將在錄音完成後轉錄）")

    parser.add_argument("-o", "--output", type=str, default="demo.mp3", help="輸出 mp3 檔名")
    parser.add_argument("-v", "--voice", type=str, default="alloy", help="TTS 語者：alloy/echo/fable/onyx/nova/shimmer")
    parser.add_argument("--system", type=str, default="", help="可選的系統前提/口吻指示（可搭配 --concise）")
    parser.add_argument("--tmp", type=str, default="input.wav", help="錄音暫存檔路徑")
    parser.add_argument("--no-s2twp", action="store_true", help="停用簡轉繁（s2twp）")
    parser.add_argument("--no-play", action="store_true", help="產生音檔但不自動播放")
    parser.add_argument("--loop", action="store_true", help="多回合互動模式（預設啟用）")
    parser.add_argument("--no-loop", action="store_true", help="停用多回合模式，只執行一次")
    parser.add_argument("--continuous", action="store_true", help="持續對話模式（自動循環，支援上下文記憶）")
    parser.add_argument("--auto-restart", action="store_true", help="持續模式中自動重新開始錄音（無需按 Enter）")
    parser.add_argument("--sd-device", type=int, default=None, help="sounddevice 輸入裝置索引")
    parser.add_argument("--adev", type=int, default=0, help="ffmpeg avfoundation 音訊裝置索引，預設 0")
    parser.add_argument("--concise", action="store_true", help="啟用簡潔回答模式（1~2 句內，少廢話）")
    parser.add_argument("--temperature", type=float, default=0.5, help="LLM 溫度（0~2，越低越保守）")
    parser.add_argument("--max-tokens", type=int, default=120, help="限制回覆最大 tokens 數")
    parser.add_argument("--wake", type=str, default=DEFAULT_WAKE, help="喚醒詞，命中時直接回覆固定句")
    parser.add_argument("--wake-reply", type=str, default=DEFAULT_WAKE_REPLY, help="喚醒詞命中時的固定回覆")
    parser.add_argument("--speed", type=float, default=1.2, help="TTS 語速倍率（1.0=正常，1.2=預設1.2倍速，1.5=1.5倍速，2.0=2倍速）")
    parser.add_argument("--rules", type=str, default="rules/badminton_rules.yaml", help="規則檔路徑（YAML）。設定後將先做規則匹配；命中則跳過 LLM")
    parser.add_argument("--no-rules", action="store_true", help="忽略規則檔（除錯用）")
    
    # 語音識別參數
    parser.add_argument("--whisper-model", type=str, default="whisper-1", help="Whisper 模型：whisper-1")
    parser.add_argument("--whisper-language", type=str, default="zh", help="Whisper 語言代碼：zh（中文）、en（英文）、ja（日文）等")
    
    # 低延遲優化參數
    parser.add_argument("--low-latency", action="store_true", help="啟用低延遲模式（減少 VAD 等待時間，跳過進度指示器）")
    parser.add_argument("--ultra-fast", action="store_true", help="啟用超快速模式（最低延遲，可能影響準確性）")
    parser.add_argument("--no-progress", action="store_true", help="跳過所有進度指示器")
    parser.add_argument("--parallel", action="store_true", help="啟用並行處理（實驗性功能）")
    
    # 預載入優化參數
    parser.add_argument("--preload", action="store_true", help="啟用預載入回覆模板系統")
    parser.add_argument("--no-preload", action="store_true", help="停用預載入系統")
    parser.add_argument("--preload-common", action="store_true", help="預載入常用回覆模板")
    parser.add_argument("--cache-stats", action="store_true", help="顯示快取統計資訊")
    parser.add_argument("--no-persistent-cache", action="store_true", help="停用持久化快取")
    parser.add_argument("--save-cache", action="store_true", help="立即儲存快取")
    parser.add_argument("--clear-cache", action="store_true", help="清空快取")
    # 規則快取參數
    parser.add_argument("--no-rule-cache", action="store_true", help="停用規則快取")
    parser.add_argument("--no-preload-rules", action="store_true", help="停用規則預載入")
    parser.add_argument("--rule-cache-ttl", type=int, default=300, help="規則快取存活時間（秒）")
    
    # 模式分流參數
    parser.add_argument("--default-mode", choices=["control","think"], default="control",
                        help="啟動預設模式：control=控制模式(無LLM)、think=思考模式(允許LLM)")
    parser.add_argument("--think-on", type=str, default="啟動思考模式",
                        help="切換到思考模式的關鍵字")
    parser.add_argument("--control-on", type=str, default="啟動控制模式",
                        help="切回控制模式的關鍵字")
    parser.add_argument("--mismatch-reply", type=str, default="我現在在控制模式，請用明確的指令再說一次。",
                        help="控制模式下規則不匹配時的回覆")
    
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    # 應用低延遲配置
    if args.low_latency or args.ultra_fast:
        app_config.low_latency_mode = True
        print("⚡ 低延遲模式已啟用")
    
    if args.ultra_fast:
        app_config.audio.silence_ms = app_config.audio.ultra_fast_silence_ms
        app_config.audio.min_speech_frames = app_config.audio.min_speech_frames_fast
        print("🚀 超快速模式已啟用")
    
    if args.no_progress:
        app_config.skip_progress_indicators = True
        print("📊 進度指示器已停用")
    
    if args.parallel:
        app_config.parallel_processing = True
        print("🔄 並行處理已啟用")
    
    # 應用預載入配置
    if args.no_preload:
        app_config.preload.enabled = False
        print("🚫 預載入系統已停用")
    elif args.preload:
        app_config.preload.enabled = True
        print("📋 預載入系統已啟用")
    
    # 應用持久化快取配置
    if args.no_persistent_cache:
        app_config.preload.persistent_cache = False
        print("🚫 持久化快取已停用")
    
    # 應用規則快取配置
    if args.no_rule_cache:
        app_config.preload.rule_cache_enabled = False
        print("🚫 規則快取已停用")
    
    if args.no_preload_rules:
        app_config.preload.preload_rules = False
        print("🚫 規則預載入已停用")
    
    if args.rule_cache_ttl != 300:
        app_config.preload.rule_cache_ttl = args.rule_cache_ttl
        print(f"⏰ 規則快取存活時間設為 {args.rule_cache_ttl} 秒")
    
    # 初始化日誌系統
    setup_logging("INFO")

    # 檢查金鑰再初始化 Client
    if os.environ.get("OPENAI_API_KEY") in (None, "", "你的key"):
        print("❌ 請先設定環境變數 OPENAI_API_KEY")
        sys.exit(1)
    client = OpenAI()
    
    # 初始化模式管理器
    mode_manager = ModeManager(
        default_mode=args.default_mode,
        think_on=args.think_on,
        control_on=args.control_on,
        mismatch_reply=args.mismatch_reply
    )
    print(f"🎛️ 模式管理器已初始化，預設模式：{mode_manager.get_current_mode()}")
    print(f"   - 切換到思考模式：{args.think_on}")
    print(f"   - 切換到控制模式：{args.control_on}")

    # 初始化預載入管理器
    preload_manager = None
    if app_config.preload.enabled:
        preload_manager = PreloadManager(client)
        preload_manager.start_background_preload()
        
        if args.preload_common:
            preload_manager.preload_common_queries()
    
    # 處理快取管理命令
    if args.save_cache:
        reply_cache.save_cache_now()
        return
    
    if args.clear_cache:
        reply_cache.clear_cache()
        return
    
    # 顯示快取統計
    if args.cache_stats:
        stats = reply_cache.get_cache_stats()
        print(f"📊 快取統計：{stats}")
        return

    # 預設為持續對話模式，除非明確指定其他模式
    if args.no_loop and not args.continuous and not args.loop:
        reply, _ = run_once(args, client, preload_manager=preload_manager, mode_manager=mode_manager)
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
        
        conversation_history = []
        round_count = 0
        
        try:
            while True:
                round_count += 1
                print(f"\n{'='*50}")
                print(f"🎯 第 {round_count} 輪對話")
                print(f"🎛️ 當前模式：{mode_manager.get_current_mode()}")
                print(f"{'='*50}")
                
                reply, conversation_history = run_once(args, client, conversation_history, preload_manager, mode_manager)
                
                if args.auto_restart:
                    print("⏳ 1 秒後自動開始下一輪...")
                    import time
                    time.sleep(1)
                else:
                    input("（按 Enter 繼續下一輪，或 Ctrl+C 結束）")
                    
        except KeyboardInterrupt:
            print(f"\n👋 已結束。總共進行了 {round_count} 輪對話。")
            # 顯示最終快取統計
            if app_config.preload.enabled:
                stats = reply_cache.get_cache_stats()
                print(f"📊 最終快取統計：{stats}")
        finally:
            # 清理預載入管理器
            if preload_manager:
                preload_manager.stop_background_preload()
            # 儲存快取
            if app_config.preload.enabled and app_config.preload.persistent_cache:
                reply_cache.save_cache_now()
        return

    # 傳統多回合模式
    print("🔁 進入多回合模式。每回合結束後按 Enter 進入下一回合，Ctrl+C 離開。")
    try:
        while True:
            reply, _ = run_once(args, client, preload_manager=preload_manager, mode_manager=mode_manager)
            input("（按 Enter 繼續下一回合，或 Ctrl+C 結束）")
    except KeyboardInterrupt:
        print("\n👋 已結束。")
        # 顯示最終快取統計
        if app_config.preload.enabled:
            stats = reply_cache.get_cache_stats()
            print(f"📊 最終快取統計：{stats}")
    finally:
        # 清理預載入管理器
        if preload_manager:
            preload_manager.stop_background_preload()
        # 儲存快取
        if app_config.preload.enabled and app_config.preload.persistent_cache:
            reply_cache.save_cache_now()


if __name__ == "__main__":
    main()
