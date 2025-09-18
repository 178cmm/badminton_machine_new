"""
🏸 羽球發球機語音控制系統 - TTS 整合版
整合 Whisper API、規則匹配系統和 TTS 語音回覆

功能特色：
1. Whisper API 高準確度語音識別
2. YAML 規則匹配系統
3. OpenAI TTS 語音回覆
4. 預載入快取優化
5. 與發球機控制系統整合
"""

import asyncio
import json
import os
import sys
import time
import logging
import threading
import re
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wavwrite
from openai import OpenAI

try:
    # 繁體轉換
    from opencc import OpenCC
    _cc = OpenCC('s2twp')
except ImportError:
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
    # 規則系統
    import yaml
    from rapidfuzz import fuzz
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False


@dataclass
class AudioConfig:
    """音訊配置"""
    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 30
    min_speech_frames: int = 10
    max_recording_ms: int = 60000
    silence_ms: int = 500
    aggressiveness: int = 2


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
class VoiceConfig:
    """語音配置"""
    audio: AudioConfig = field(default_factory=AudioConfig)
    default_voice: str = "nova"
    default_speed: float = 1.2
    whisper_model: str = "whisper-1"
    whisper_language: str = "zh"
    rules_path: str = "rules/badminton_rules.yaml"
    enable_tts: bool = True
    enable_rules: bool = True
    safe_mode: bool = True  # 安全模式，減少記憶體使用和錯誤處理
    # 預載入配置
    preload: PreloadConfig = field(default_factory=PreloadConfig)


# 全域配置
voice_config = VoiceConfig()

# 規則快取
_RULES_CACHE = {"path": None, "mtime": 0.0, "data": None}

# === 預載入回覆模板系統 ===
class ReplyTemplateCache:
    """回覆模板快取系統（支援持久化）"""
    
    def __init__(self, config: PreloadConfig):
        self.config = config
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
        if not (self.config.enabled and self.config.rule_cache_enabled):
            return
        
        query_hash = self._hash_query(query)
        self.rule_cache[query_hash] = {
            "rule": rule_result,
            "timestamp": time.time(),
            "count": 1
        }
    
    def get_cached_rule_result(self, query: str) -> Optional[dict]:
        """獲取快取的規則匹配結果"""
        if not (self.config.enabled and self.config.rule_cache_enabled):
            return None
        
        query_hash = self._hash_query(query)
        if query_hash in self.rule_cache:
            cached = self.rule_cache[query_hash]
            # 檢查快取是否過期
            if time.time() - cached["timestamp"] < self.config.rule_cache_ttl:
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
        if not self.config.enabled:
            return None
        
        query_hash = self._hash_query(query)
        if query_hash in self.cache:
            cached = self.cache[query_hash]
            # 檢查快取是否過期
            if time.time() - cached["timestamp"] < self.config.cache_ttl:
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
        if not self.config.prediction_enabled:
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
        if not self.config.persistent_cache:
            return
        
        cache_file = self.config.cache_file
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
                    if time.time() - cache_data["timestamp"] < self.config.cache_ttl:
                        self.cache[query_hash] = cache_data
                
                print(f"📂 載入持久化快取：{len(self.cache)} 個項目")
            else:
                print("📂 未找到快取檔案，將建立新的快取")
                
        except Exception as e:
            print(f"⚠️ 載入快取失敗：{e}")
    
    def _save_persistent_cache(self):
        """儲存持久化快取"""
        if not self.config.persistent_cache:
            return
        
        cache_file = self.config.cache_file
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
        return (time.time() - self.last_save_time) >= self.config.auto_save_interval
    
    def cache_reply(self, query: str, reply: str):
        """快取回覆（支援自動儲存）"""
        if not self.config.enabled:
            return
        
        query_hash = self._hash_query(query)
        
        # 檢查快取大小限制
        if len(self.cache) >= self.config.max_cache_size:
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
            "persistent_cache": self.config.persistent_cache,
            "cache_file": self.config.cache_file,
            "last_save": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_save_time))
        }
    
    def save_cache_now(self):
        """立即儲存快取"""
        self._save_persistent_cache()
    
    def clear_cache(self):
        """清空快取"""
        self.cache.clear()
        self.rule_cache.clear()
        if self.config.persistent_cache:
            self._save_persistent_cache()
        print("🗑️ 快取已清空")

# === 預載入管理器 ===
class PreloadManager:
    """預載入管理器"""
    
    def __init__(self, client: OpenAI, reply_cache: ReplyTemplateCache):
        self.client = client
        self.reply_cache = reply_cache
        self.preload_thread = None
        self.is_running = False
        self.preload_queue = []
    
    def start_background_preload(self):
        """啟動背景預載入執行緒"""
        if not self.reply_cache.config.enabled:
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
                if self.reply_cache.prediction_queue:
                    prediction = self.reply_cache.prediction_queue.pop(0)
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
            if self.reply_cache.get_cached_reply(query):
                return
            
            # 首先檢查規則匹配
            rule_result = self._preload_rule_match(query)
            if rule_result:
                return
            
            # 檢查是否有常用回覆模板
            common_reply = self.reply_cache.get_common_reply(query)
            if common_reply:
                self.reply_cache.cache_reply(query, common_reply)
                return
            
            # 使用 LLM 生成回覆（低優先級）
            if len(self.reply_cache.cache) < self.reply_cache.config.max_cache_size // 2:
                reply = self._generate_preload_reply(query)
                if reply:
                    self.reply_cache.cache_reply(query, reply)
        
        except Exception as e:
            print(f"⚠️ 預載入回覆失敗：{e}")
    
    def _preload_rule_match(self, query: str) -> bool:
        """預載入規則匹配結果"""
        if not self.reply_cache.config.preload_rules:
            return False
            
        try:
            # 使用預設規則檔案進行匹配
            default_rules_path = "rules/badminton_rules.yaml"
            if os.path.exists(default_rules_path):
                matcher = RuleMatcher(default_rules_path)
                hit = matcher.match(query)
                if hit:
                    # 快取規則匹配結果
                    self.reply_cache.cache_rule_result(query, hit)
                    
                    # 生成並快取回覆
                    context = {"balls_left": 48}
                    reply_text = format_reply(hit.get("reply", {}).get("text", ""), context)
                    self.reply_cache.cache_reply(query, reply_text)
                    return True
        except Exception as e:
            print(f"⚠️ 預載入規則匹配失敗：{e}")
        
        return False
    
    def _generate_preload_reply(self, query: str) -> Optional[str]:
        """生成預載入回覆"""
        try:
            # 使用簡潔的系統提示
            system_prompt = "你是羽球發球機助理，請用簡潔的1-2句話回覆。"
            
            # 簡化的 LLM 回覆生成
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
        
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

# === 進度指示器系統 ===
def show_progress(message: str, duration: float = 0.5, show_dots: bool = True):
    """顯示進度指示"""
    print(f"⏳ {message}", end="", flush=True)
    if show_dots:
        time.sleep(duration)
        print(" ✅")
    else:
        print()

def show_fast_progress(message: str):
    """快速進度指示（無延遲）"""
    print(f"⚡ {message}")

def show_progress_with_dots(message: str, total_steps: int = 3):
    """顯示帶點點的進度指示"""
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
        max_frames = 1000  # 預設最大緩衝區幀數
    
    if len(audio_buffer) > max_frames:
        # 只保留最近的音訊幀，釋放舊的記憶體
        return audio_buffer[-max_frames:]
    return audio_buffer

def _cleanup_old_frames(audio_buffer: list, threshold: Optional[int] = None) -> list:
    """清理舊的音訊幀以釋放記憶體"""
    if threshold is None:
        threshold = 500  # 預設緩衝區清理閾值
    
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

# 中文標點符號
_ZH_PUNCT = "，。！？、；：「」『』（）【】《》—．…‧,.!?;:()[]{}<>~`@#$%^&*-_=+|/\\\"'\u3000 "


def _normalize_zh(s: str) -> str:
    """正規化中文文本"""
    s = (s or "").strip().lower()
    for ch in _ZH_PUNCT:
        s = s.replace(ch, "")
    return s


def s2twp(text: str, enabled: bool = True) -> str:
    """簡體轉繁體"""
    if not enabled or not text:
        return text
    if _cc is None:
        return text
    return _cc.convert(text)


class RuleMatcher:
    """規則匹配器"""
    
    def __init__(self, rules_path: str):
        self.rules_path = rules_path
        self._rules_data = None
        self._last_mtime = 0.0
    
    def _load_rules(self) -> dict:
        """載入規則檔案"""
        global _RULES_CACHE
        p = os.path.abspath(self.rules_path)
        
        if not os.path.exists(p):
            print(f"⚠️ 規則檔案不存在：{p}")
            return {"rules": []}
        
        mtime = os.path.getmtime(p)
        
        # 檢查快取
        if (_RULES_CACHE["path"] == p and 
            _RULES_CACHE["mtime"] == mtime and 
            _RULES_CACHE["data"] is not None):
            return _RULES_CACHE["data"]
        
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            # 預處理規則
            for r in data.get("rules", []):
                r.setdefault("priority", 0)
                r.setdefault("match", {})
                r["match"].setdefault("contains", [])
                r["match"].setdefault("regex", [])
                r["match"].setdefault("fuzzy", [])
                
                # 預建正規化字串
                r["_contains_norm"] = [_normalize_zh(x) for x in r["match"]["contains"]]
            
            # 更新快取
            _RULES_CACHE = {"path": p, "mtime": mtime, "data": data}
            return data
            
        except Exception as e:
            print(f"⚠️ 載入規則檔案失敗：{e}")
            return {"rules": []}
    
    def match(self, text: str) -> Optional[dict]:
        """匹配規則"""
        if not text.strip():
            return None
        
        rules_data = self._load_rules()
        ntext = _normalize_zh(text)
        rules = sorted(rules_data.get("rules", []), 
                      key=lambda r: r.get("priority", 0), reverse=True)
        fuzzy_th = rules_data.get("globals", {}).get("fuzzy_threshold", 86)

        for r in rules:
            # 包含式匹配
            for key_norm in r.get("_contains_norm", []):
                if key_norm and key_norm in ntext:
                    return r
            
            # 正則匹配
            for pat in r["match"].get("regex", []):
                try:
                    if re.search(pat, text):
                        return r
                except re.error:
                    continue
            
            # 模糊匹配
            for k in r["match"].get("fuzzy", []):
                if fuzz.partial_ratio(ntext, _normalize_zh(k)) >= fuzzy_th:
                    return r
        
        return None


class VoiceControlTTS:
    """
    語音控制系統 - TTS 整合版
    支援 Whisper API 語音識別、規則匹配和 TTS 回覆
    """
    
    def __init__(self, window, config: Optional[VoiceConfig] = None):
        self.window = window
        self.config = config or voice_config
        
        # OpenAI 客戶端
        self.client = None
        self._init_openai_client()
        
        # 音訊相關
        self._audio_stream = None
        self._running = False
        self._starting = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._listen_task: Optional[asyncio.Task] = None
        self._capture_task: Optional[asyncio.Task] = None
        self._start_stop_lock = asyncio.Lock()
        
        # 規則匹配器
        self.rule_matcher = None
        if self.config.enable_rules and RULES_AVAILABLE:
            self.rule_matcher = RuleMatcher(self.config.rules_path)
        
        # 音訊緩存
        self._audio_buffer = []
        self._vad = None
        
        # 設備配置
        self.input_device = None
        
        # 預載入系統
        self.reply_cache = None
        self.preload_manager = None
        if self.config.preload.enabled:
            self.reply_cache = ReplyTemplateCache(self.config.preload)
            if self.client:
                self.preload_manager = PreloadManager(self.client, self.reply_cache)
        
        # 模式管理器
        self.mode_manager = ModeManager(
            default_mode="control",
            think_on="啟動思考模式",
            control_on="啟動控制模式",
            mismatch_reply="我現在在控制模式，請用明確的指令再說一次。"
        )
        
        # 對話歷史
        self.conversation_history = []
    
    def _init_openai_client(self):
        """初始化 OpenAI 客戶端"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "你的key":
            self._log_ui("❌ 請設定環境變數 OPENAI_API_KEY")
            return
        
        try:
            self.client = OpenAI(api_key=api_key)
            self._log_ui("✅ OpenAI 客戶端初始化成功")
        except Exception as e:
            self._log_ui(f"❌ OpenAI 客戶端初始化失敗：{e}")
    
    def set_input_device(self, device_index: Optional[int]):
        """設定輸入裝置"""
        self.input_device = device_index
    
    async def start(self):
        """啟動語音控制"""
        if self._running or self._starting:
            self._add_chat_message("⚠️ 語音控制已經在運行中", "system")
            return
        
        async with self._start_stop_lock:
            if self._running or self._starting:
                self._add_chat_message("⚠️ 語音控制已經在運行中", "system")
                return
            self._starting = True
            self._update_status("正在啟動語音控制...", "main")
        
        # 檢查依賴
        if not self._check_dependencies():
            self._starting = False
            return
        
        try:
            # 初始化 VAD（優先使用 VAD，安全模式作為備選）
            if WEBRTCVAD_AVAILABLE:
                try:
                    self._vad = webrtcvad.Vad(self.config.audio.aggressiveness)
                    self._log_ui("✅ VAD 已啟用")
                except Exception as e:
                    self._log_ui(f"⚠️ VAD 初始化失敗，使用固定時長模式：{e}")
                    self._vad = None
            else:
                self._vad = None
                self._log_ui("⚠️ webrtcvad 未安裝，使用固定時長錄音")
                if self.config.safe_mode:
                    self._log_ui("🛡️ 安全模式：使用固定時長錄音")
            
            # 設定音訊流（不設置 _running 狀態）
            await self._setup_audio_stream()
            
            # 啟動預載入系統
            if self.preload_manager:
                self.preload_manager.start_background_preload()
                self.preload_manager.preload_common_queries()
                self._log_ui("📋 預載入系統已啟動")
            
            # 設置運行狀態
            self._running = True
            
            # 啟動監聽
            self._listen_task = asyncio.create_task(self._listen_loop())
            self._add_chat_message("🎙️ 語音控制已啟動，請開始說話...", "system")
            self._add_chat_message(f"🎛️ 當前模式：{self.mode_manager.get_current_mode()}", "system")
            self._update_status("語音控制運行中", "main")
            self._update_status("等待語音輸入...", "processing")
            
        except Exception as e:
            self._log_ui(f"❌ 啟動語音控制失敗：{e}")
            self._running = False
        finally:
            self._starting = False
    
    async def stop(self):
        """停止語音控制"""
        async with self._start_stop_lock:
            if not self._running and not self._starting:
                return
            self._starting = False
        
        self._running = False
        self._update_status("正在停止語音控制...", "main")
        
        # 停止預載入系統
        if self.preload_manager:
            self.preload_manager.stop_background_preload()
            self._add_chat_message("📋 預載入系統已停止", "system")
        
        # 儲存快取
        if self.reply_cache:
            self.reply_cache.save_cache_now()
            self._log_ui("💾 快取已儲存")
        
        # 停止監聽任務
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        # 停止音訊捕獲
        if self._capture_task and not self._capture_task.done():
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
        
        # 簡化版：不需要關閉音訊流
        self._audio_stream = None
        
        # 清理任務引用
        self._listen_task = None
        self._capture_task = None
        
        self._add_chat_message("🔇 語音控制已停止", "system")
        self._update_status("語音控制未啟動", "main")
        self._update_status("等待語音輸入...", "processing")
    
    def force_reset(self):
        """強制重置狀態（用於調試）"""
        self._running = False
        self._starting = False
        self._listen_task = None
        self._capture_task = None
        self._audio_stream = None
        self._log_ui("🔄 語音控制狀態已強制重置")
    
    def _check_dependencies(self) -> bool:
        """檢查依賴套件"""
        if not self.client:
            self._log_ui("❌ OpenAI 客戶端未初始化")
            return False
        
        if sd is None:
            self._log_ui("❌ sounddevice 未安裝")
            return False
        
        if not WEBRTCVAD_AVAILABLE:
            self._log_ui("⚠️ webrtcvad 未安裝，將使用固定時長錄音")
        
        if self.config.enable_rules and not RULES_AVAILABLE:
            self._log_ui("⚠️ 規則系統依賴未安裝（pyyaml, rapidfuzz）")
        
        return True
    
    async def _setup_audio_stream(self):
        """設定音訊流（簡化版，避免複雜的音訊流處理）"""
        try:
            # 檢查音訊裝置
            try:
                devices = sd.query_devices()
                if self.input_device is not None:
                    if self.input_device >= len(devices):
                        self._log_ui(f"⚠️ 音訊裝置索引 {self.input_device} 超出範圍，使用預設裝置")
                        self.input_device = None
                    elif devices[self.input_device].get('max_input_channels', 0) == 0:
                        self._log_ui(f"⚠️ 裝置 {self.input_device} 不支援輸入，使用預設裝置")
                        self.input_device = None
            except Exception as e:
                self._log_ui(f"⚠️ 查詢音訊裝置失敗：{e}")
                self.input_device = None
            
            self._log_ui(f"🎤 音訊裝置設定：採樣率 {self.config.audio.sample_rate}Hz，裝置 {self.input_device or 'default'}")
            
            # 簡化版：不使用複雜的音訊流，改為按需錄音
            self._log_ui("✅ 音訊系統初始化完成（簡化模式）")
            
        except Exception as e:
            self._log_ui(f"❌ 音訊系統初始化失敗：{e}")
            raise RuntimeError(f"音訊系統初始化失敗：{e}")
    
    async def _capture_loop(self):
        """音訊捕獲循環（簡化版，改為按需錄音）"""
        # 簡化版：不使用持續的音訊捕獲，改為按需錄音
        while self._running:
            try:
                # 等待錄音請求
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log_ui(f"⚠️ 音訊捕獲循環錯誤：{e}")
                await asyncio.sleep(0.1)
    
    async def _listen_loop(self):
        """語音監聽主循環（簡化版，改為按需錄音）"""
        self._log_ui("🎙️ 開始語音監聽循環...")
        consecutive_failures = 0
        max_failures = 5  # 最多連續失敗5次後停止
        
        # 確保在循環開始前檢查狀態
        if not self._running:
            self._log_ui("⚠️ 監聽循環啟動時發現 _running 為 False")
            return
        
        while self._running:
            try:
                # 檢查運行狀態
                if not self._running:
                    self._log_ui("🛑 檢測到停止信號，退出監聽循環")
                    break
                
                self._log_ui("🔄 監聽循環：準備錄音...")
                
                # 簡化版：使用固定時長錄音，類似簡化版的方式
                audio_data = await self._record_audio_simple()
                
                # 再次檢查運行狀態
                if not self._running:
                    self._log_ui("🛑 錄音完成後檢測到停止信號，退出監聽循環")
                    break
                
                if not audio_data:
                    consecutive_failures += 1
                    self._log_ui(f"⚠️ 錄音失敗 ({consecutive_failures}/{max_failures})，等待2秒後重試...")
                    if consecutive_failures >= max_failures:
                        self._log_ui("❌ 錄音連續失敗次數過多，停止語音控制")
                        break
                    await asyncio.sleep(2)  # 等待2秒後再次嘗試
                    continue
                
                # 重置失敗計數
                consecutive_failures = 0
                self._log_ui(f"✅ 錄音成功，數據大小：{len(audio_data)} bytes")
                
                # 語音識別
                self._log_ui("🔄 開始語音識別...")
                text = await self._transcribe_audio(audio_data)
                
                # 再次檢查運行狀態
                if not self._running:
                    self._log_ui("🛑 語音識別完成後檢測到停止信號，退出監聽循環")
                    break
                
                if not text.strip():
                    self._log_ui("⚠️ 語音識別結果為空，等待2秒後重試...")
                    await asyncio.sleep(2)  # 等待2秒後再次嘗試
                    continue
                
                self._log_ui(f"🎤 識別結果：{text}")
                
                # 處理指令
                self._log_ui("🔄 開始處理指令...")
                await self._process_command(text)
                
                # 處理完一個指令後等待一段時間
                self._log_ui("✅ 指令處理完成，等待3秒後繼續監聽...")
                await asyncio.sleep(3)
                
            except asyncio.CancelledError:
                self._log_ui("🛑 監聽循環被取消")
                break
            except Exception as e:
                consecutive_failures += 1
                self._log_ui(f"⚠️ 處理語音時發生錯誤 ({consecutive_failures}/{max_failures})：{e}")
                if consecutive_failures >= max_failures:
                    self._log_ui("❌ 錯誤次數過多，停止語音控制")
                    break
                await asyncio.sleep(2)
    
    async def _record_audio(self) -> Optional[bytes]:
        """錄音並返回音訊數據"""
        audio_buffer = []
        max_buffer_size = 1000  # 限制緩衝區大小
        
        try:
            if self._vad and WEBRTCVAD_AVAILABLE:
                # 使用 VAD 自動停止錄音
                consecutive_silence = 0
                has_speech = False
                speech_frames = 0
                
                frame_size = int(self.config.audio.sample_rate * 
                               self.config.audio.frame_duration_ms / 1000)
                silence_frames = int(self.config.audio.silence_ms / 
                                   self.config.audio.frame_duration_ms)
                
                timeout_count = 0
                max_timeouts = 50  # 最多等待 5 秒
                
                while self._running and timeout_count < max_timeouts:
                    try:
                        # 等待音訊數據
                        data = await asyncio.wait_for(self._audio_queue.get(), timeout=0.1)
                        timeout_count = 0  # 重置超時計數
                        
                        # 安全地轉換為 numpy array
                        try:
                            audio_frame = np.frombuffer(data, dtype=np.int16)
                        except Exception as e:
                            self._log_ui(f"⚠️ 音訊數據轉換失敗：{e}")
                            continue
                        
                        # VAD 檢測
                        if len(audio_frame) >= frame_size:
                            try:
                                frame_bytes = audio_frame[:frame_size].tobytes()
                                is_speech = self._vad.is_speech(frame_bytes, 
                                                              self.config.audio.sample_rate)
                                
                                if is_speech:
                                    consecutive_silence = 0
                                    has_speech = True
                                    speech_frames += 1
                                else:
                                    consecutive_silence += 1
                                
                                # 限制緩衝區大小避免記憶體問題
                                if len(audio_buffer) < max_buffer_size:
                                    audio_buffer.append(audio_frame)
                                else:
                                    # 移除最舊的幀
                                    audio_buffer.pop(0)
                                    audio_buffer.append(audio_frame)
                                
                                # 檢查是否應該停止錄音
                                if (has_speech and 
                                    speech_frames >= self.config.audio.min_speech_frames and 
                                    consecutive_silence >= silence_frames):
                                    break
                                
                                # 防止錄音過長
                                if len(audio_buffer) * self.config.audio.frame_duration_ms > self.config.audio.max_recording_ms:
                                    break
                                    
                            except Exception as e:
                                self._log_ui(f"⚠️ VAD 檢測失敗：{e}")
                                continue
                        
                    except asyncio.TimeoutError:
                        timeout_count += 1
                        continue
                    except Exception as e:
                        self._log_ui(f"⚠️ 錄音數據處理錯誤：{e}")
                        break
            else:
                # 固定時長錄音（2秒，減少時間）
                duration = 2.0
                frames_needed = min(int(duration * self.config.audio.sample_rate / 4000), max_buffer_size)
                
                for _ in range(frames_needed):
                    try:
                        data = await asyncio.wait_for(self._audio_queue.get(), timeout=0.1)
                        try:
                            audio_frame = np.frombuffer(data, dtype=np.int16)
                            audio_buffer.append(audio_frame)
                        except Exception as e:
                            self._log_ui(f"⚠️ 音訊幀處理錯誤：{e}")
                            continue
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        self._log_ui(f"⚠️ 固定時長錄音錯誤：{e}")
                        break
            
            # 合併音訊數據
            if audio_buffer:
                try:
                    full_audio = np.concatenate(audio_buffer, axis=0)
                    audio_bytes = full_audio.tobytes()
                    
                    # 清理記憶體
                    del audio_buffer
                    del full_audio
                    
                    return audio_bytes
                except Exception as e:
                    self._log_ui(f"⚠️ 音訊合併失敗：{e}")
                    return None
            
            return None
            
        except Exception as e:
            self._log_ui(f"⚠️ 錄音過程發生錯誤：{e}")
            # 清理記憶體
            if audio_buffer:
                del audio_buffer
            return None
    
    async def _record_audio_simple(self) -> Optional[bytes]:
        """錄音方法（優先使用 VAD，備選固定時長）"""
        try:
            # 如果有 VAD，使用 VAD 錄音
            if self._vad and WEBRTCVAD_AVAILABLE:
                return await self._record_with_vad()
            else:
                # 備選：固定時長錄音
                return await self._record_fixed_duration()
            
        except Exception as e:
            self._log_ui(f"⚠️ 錄音失敗：{e}")
            return None
    
    async def _record_with_vad(self) -> Optional[bytes]:
        """使用 VAD 自動偵測語音結束的錄音方法"""
        try:
            # 檢查 VAD 是否正確初始化
            if not self._vad:
                self._log_ui("❌ VAD 未初始化，無法使用 VAD 錄音")
                return None
            
            self._log_ui("🎤 開始 VAD 錄音，偵測到靜音時自動停止...")
            
            def record_with_vad():
                """VAD 錄音函數（參考 main.py 的實現）"""
                try:
                    # 設定 sounddevice 參數
                    if self.input_device is not None:
                        sd.default.device = (self.input_device, None)
                    sd.default.samplerate = self.config.audio.sample_rate
                    sd.default.channels = self.config.audio.channels
                    
                    # VAD 參數
                    frame_duration_ms = self.config.audio.frame_duration_ms
                    frame_size = int(self.config.audio.sample_rate * frame_duration_ms / 1000)
                    silence_frames = int(self.config.audio.silence_ms / frame_duration_ms)
                    min_speech_frames = self.config.audio.min_speech_frames
                    
                    # 開始錄音
                    audio_buffer = []
                    consecutive_silence = 0
                    has_speech = False
                    speech_frames = 0
                    
                    with sd.InputStream(samplerate=self.config.audio.sample_rate,
                                      channels=self.config.audio.channels,
                                      dtype="int16", blocksize=frame_size) as stream:
                        while True:
                            # 讀取一幀音訊
                            audio_frame, overflowed = stream.read(frame_size)
                            if overflowed:
                                print("⚠️ 音訊緩衝區溢出")
                            
                            # 轉換為 bytes 供 VAD 使用
                            frame_bytes = audio_frame.tobytes()
                            
                            # VAD 偵測
                            is_speech = self._vad.is_speech(frame_bytes, self.config.audio.sample_rate)
                            
                            if is_speech:
                                consecutive_silence = 0
                                has_speech = True
                                speech_frames += 1
                            else:
                                consecutive_silence += 1
                            
                            # 儲存音訊幀
                            audio_buffer.append(audio_frame)
                            
                            # 檢查是否應該停止
                            if (has_speech and 
                                speech_frames >= min_speech_frames and 
                                consecutive_silence >= silence_frames):
                                print("🔇 偵測到靜音，停止錄音")
                                break
                            
                            # 防止錄音過長
                            if len(audio_buffer) * frame_duration_ms > self.config.audio.max_recording_ms:
                                print("⏰ 錄音時間過長，自動停止")
                                break
                    
                    # 合併音訊
                    if audio_buffer:
                        full_audio = np.concatenate(audio_buffer, axis=0)
                        return full_audio
                    else:
                        return None
                        
                except Exception as e:
                    raise RuntimeError(f"VAD 錄音過程失敗：{e}")
            
            # 在執行緒中執行錄音
            loop = asyncio.get_running_loop()
            try:
                audio = await asyncio.wait_for(
                    loop.run_in_executor(None, record_with_vad),
                    timeout=30.0  # 最多30秒超時
                )
                
                if audio is not None and len(audio) > 0:
                    audio_bytes = audio.tobytes()
                    self._log_ui(f"✅ VAD 錄音完成，數據大小：{len(audio_bytes)} bytes")
                    return audio_bytes
                else:
                    self._log_ui("⚠️ VAD 錄音數據為空")
                    return None
                    
            except asyncio.TimeoutError:
                self._log_ui("⚠️ VAD 錄音超時")
                return None
            
        except Exception as e:
            self._log_ui(f"⚠️ VAD 錄音失敗：{e}")
            return None
    
    async def _record_fixed_duration(self) -> Optional[bytes]:
        """固定時長錄音方法（備選方案）"""
        try:
            duration = 3.0  # 3秒錄音
            sample_rate = self.config.audio.sample_rate
            
            self._log_ui(f"🎤 開始固定時長錄音 {duration} 秒...")
            
            def record_audio():
                """錄音函數"""
                try:
                    # 設定 sounddevice 預設參數
                    if self.input_device is not None:
                        sd.default.device = (self.input_device, None)
                    sd.default.samplerate = sample_rate
                    sd.default.channels = self.config.audio.channels
                    
                    # 開始錄音
                    audio = sd.rec(int(duration * sample_rate), dtype="int16")
                    
                    # 等待錄音完成
                    import time
                    time.sleep(duration)
                    
                    return audio
                except Exception as e:
                    raise RuntimeError(f"固定時長錄音過程失敗：{e}")
            
            # 在執行緒中執行錄音
            loop = asyncio.get_running_loop()
            try:
                audio = await asyncio.wait_for(
                    loop.run_in_executor(None, record_audio),
                    timeout=duration + 5.0
                )
                
                if audio is not None and len(audio) > 0:
                    audio_bytes = audio.tobytes()
                    self._log_ui(f"✅ 固定時長錄音完成，數據大小：{len(audio_bytes)} bytes")
                    return audio_bytes
                else:
                    self._log_ui("⚠️ 固定時長錄音數據為空")
                    return None
                    
            except asyncio.TimeoutError:
                self._log_ui("⚠️ 固定時長錄音超時")
                return None
            
        except Exception as e:
            self._log_ui(f"⚠️ 固定時長錄音失敗：{e}")
            return None
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """使用 Whisper API 轉錄音訊"""
        if not self.client:
            return ""
        
        self._update_status("ASR語音轉錄中...", "processing")
        temp_path = None
        try:
            # 檢查音訊數據
            if not audio_data or len(audio_data) < 1000:  # 太短的音訊
                return ""
            
            # 將音訊數據保存為臨時文件
            import tempfile
            import time
            temp_path = f"temp_audio_{int(time.time())}.wav"
            
            try:
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                if len(audio_array) == 0:
                    return ""
                
                wavwrite(temp_path, self.config.audio.sample_rate, audio_array)
                
                # 檢查文件是否成功創建
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) < 1000:
                    return ""
                    
            except Exception as e:
                self._log_ui(f"⚠️ 音訊文件創建失敗：{e}")
                return ""
            
            # 使用 Whisper API
            try:
                with open(temp_path, "rb") as audio_file:
                    transcript = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.client.audio.transcriptions.create(
                            model=self.config.whisper_model,
                            file=audio_file,
                            language=self.config.whisper_language,
                            response_format="text"
                        )
                    )
                
                # 處理轉錄結果
                if transcript:
                    text = transcript.strip() if isinstance(transcript, str) else str(transcript).strip()
                    if text:
                        # 轉換為繁體中文
                        result = s2twp(text)
                        return result
                        
            except Exception as e:
                self._log_ui(f"⚠️ Whisper API 調用失敗：{e}")
                return ""
            
            return ""
            
        except Exception as e:
            self._log_ui(f"⚠️ 語音轉錄過程發生錯誤：{e}")
            return ""
        finally:
            # 清理臨時文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    
    async def _process_command(self, text: str):
        """處理語音指令（整合所有新功能）"""
        # 顯示用戶語音輸入
        self._add_chat_message(text, "user")
        self._update_status("LLM分析中...", "processing")
        
        # 1. 檢查模式切換（優先處理）
        mode_switch_reply = self.mode_manager.check_mode_switch(text)
        if mode_switch_reply:
            self._add_chat_message(f"🔄 模式切換：{mode_switch_reply}", "system")
            if self.config.enable_tts:
                self._update_status("TTS語音合成中...", "processing")
                await self._speak_text(mode_switch_reply)
            self._update_status("等待語音輸入...", "processing")
            return
        
        # 2. 檢查快取回覆
        if self.reply_cache:
            cached_reply = self.reply_cache.get_cached_reply(text)
            if cached_reply:
                self._add_chat_message("⚡ 使用快取回覆", "system")
                self._add_chat_message(cached_reply, "ai")
                if self.config.enable_tts:
                    self._update_status("TTS語音合成中...", "processing")
                    await self._speak_text(cached_reply)
                
                # 預測後續可能的問題
                if self.preload_manager:
                    self.reply_cache.predict_and_preload(text, self.conversation_history)
                self._update_status("等待語音輸入...", "processing")
                return
        
        # 3. 檢查常用回覆模板
        if self.reply_cache:
            common_reply = self.reply_cache.get_common_reply(text)
            if common_reply:
                self._add_chat_message("📋 使用常用回覆模板", "system")
                self._add_chat_message(common_reply, "ai")
                if self.config.enable_tts:
                    self._update_status("TTS語音合成中...", "processing")
                    await self._speak_text(common_reply)
                
                # 快取這個回覆
                self.reply_cache.cache_reply(text, common_reply)
                
                # 預測後續可能的問題
                if self.preload_manager:
                    self.reply_cache.predict_and_preload(text, self.conversation_history)
                self._update_status("等待語音輸入...", "processing")
                return
        
        # 4. 檢查喚醒詞
        wake_word = "啟動語音發球機"
        if self._is_wake_word(text, wake_word):
            self._add_chat_message(f"🔔 喚醒詞命中：{wake_word}", "system")
            reply_text = "彥澤您好，我是你的智慧羽球發球機助理，今天想練什麼呢？"
            self._add_chat_message(reply_text, "ai")
            
            # 快取回覆
            if self.reply_cache:
                self.reply_cache.cache_reply(text, reply_text)
            
            if self.config.enable_tts:
                self._update_status("TTS語音合成中...", "processing")
                await self._speak_text(reply_text)
            self._update_status("等待語音輸入...", "processing")
            return
        
        # 5. 規則匹配
        if self.rule_matcher:
            self._add_chat_message("🔍 開始規則匹配...", "system")
            rule = self.rule_matcher.match(text)
            if rule:
                self._add_chat_message(f"✅ 找到匹配規則：{rule.get('id', 'unknown')}", "system")
                await self._handle_rule_match(rule, text)
                return
            else:
                self._add_chat_message("❌ 沒有找到匹配的規則", "system")
        else:
            self._add_chat_message("⚠️ 規則匹配器未初始化", "system")
        
        # 6. LLM 回覆（只有在思考模式下才使用）
        if self.mode_manager.is_think_mode():
            self._add_chat_message("🤖 使用 LLM 生成回覆...", "system")
            self._update_status("LLM思考中...", "processing")
            try:
                # 使用 LLM 生成回覆
                system_prompt = "你是羽球發球機助理，請用簡潔的1-2句話回覆。"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
                
                # 添加對話歷史
                if self.conversation_history:
                    messages = [{"role": "system", "content": system_prompt}] + self.conversation_history[-10:] + [{"role": "user", "content": text}]
                
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        temperature=0.5,
                        max_tokens=120
                    )
                )
                
                reply_text = response.choices[0].message.content.strip()
                self._add_chat_message(reply_text, "ai")
                
                # 快取回覆
                if self.reply_cache:
                    self.reply_cache.cache_reply(text, reply_text)
                
                # 更新對話歷史
                self.conversation_history.append({"role": "user", "content": text})
                self.conversation_history.append({"role": "assistant", "content": reply_text})
                
                # 限制對話歷史長度
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                
                if self.config.enable_tts:
                    self._update_status("TTS語音合成中...", "processing")
                    await self._speak_text(reply_text)
                self._update_status("等待語音輸入...", "processing")
                return
                
            except Exception as e:
                self._add_chat_message(f"❌ LLM 回覆失敗：{e}", "error")
        
        # 7. 控制模式下規則不匹配時的回覆
        if self.mode_manager.is_control_mode():
            reply_text = self.mode_manager.get_mismatch_reply()
            self._add_chat_message(reply_text, "ai")
            if self.config.enable_tts:
                self._update_status("TTS語音合成中...", "processing")
                await self._speak_text(reply_text)
        else:
            # 思考模式下也沒有生成回覆
            self._add_chat_message("❓ 未識別的指令，請使用明確的羽球訓練指令", "system")
        
        self._update_status("等待語音輸入...", "processing")
    
    def _is_wake_word(self, text: str, wake_word: str) -> bool:
        """檢查是否為喚醒詞（KWS）"""
        # 移除空白和標點符號進行比較
        def normalize_text(s: str) -> str:
            import re
            # 移除標點符號和空白
            s = re.sub(r'[^\w\u4e00-\u9fff]', '', s.lower())
            return s
        
        normalized_text = normalize_text(text)
        normalized_wake = normalize_text(wake_word)
        
        return normalized_wake in normalized_text
    
    async def _handle_rule_match(self, rule: dict, original_text: str):
        """處理規則匹配結果"""
        rule_id = rule.get("id", "unknown")
        action = rule.get("action", "")
        reply_config = rule.get("reply", {})
        reply_text = reply_config.get("text", "")
        voice = reply_config.get("voice", self.config.default_voice)
        
        self._log_ui(f"✅ 匹配規則：{rule_id}")
        self._log_ui(f"💬 回覆：{reply_text}")
        
        # 快取規則匹配結果
        if self.reply_cache:
            self.reply_cache.cache_rule_result(original_text, rule)
            self.reply_cache.cache_reply(original_text, reply_text)
        
        # TTS 語音回覆
        if self.config.enable_tts and reply_text:
            await self._speak_text(reply_text, voice)
        
        # 更新對話歷史
        self.conversation_history.append({"role": "user", "content": original_text})
        self.conversation_history.append({"role": "assistant", "content": reply_text})
        
        # 限制對話歷史長度
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        # 預測後續可能的問題
        if self.preload_manager:
            self.reply_cache.predict_and_preload(original_text, self.conversation_history)
        
        # 執行動作
        await self._execute_action(action, rule, original_text)
    
    async def _speak_text(self, text: str, voice: str = None):
        """TTS 語音合成並播放"""
        if not self.client or not text:
            return
        
        try:
            voice = voice or self.config.default_voice
            output_path = "temp_speech.mp3"
            
            # 生成語音
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text,
                    speed=self.config.default_speed
                )
            )
            
            # 保存音訊文件
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            # 播放音訊（macOS）
            import subprocess
            try:
                subprocess.run(["afplay", output_path], check=False)
            except Exception:
                pass
            
            # 清理臨時文件
            if os.path.exists(output_path):
                os.remove(output_path)
                
        except Exception as e:
            self._log_ui(f"⚠️ TTS 語音合成失敗：{e}")
    
    async def _execute_action(self, action: str, rule: dict, original_text: str):
        """執行動作"""
        if not action:
            return
        
        try:
            # 根據動作類型執行相應的發球機控制
            if action == "scan_device":
                await self._scan_device()
            elif action == "connect_device":
                await self._connect_device()
            elif action == "disconnect_device":
                await self._disconnect_device()
            elif action == "start_training":
                await self._start_training()
            elif action == "stop_training":
                await self._stop_training()
            elif action.startswith("set_speed_"):
                speed = action.split("_")[-1]  # fast, slow, medium
                await self._set_speed(speed)
            elif action.endswith("_training"):
                training_type = action.replace("_training", "")
                await self._start_specific_training(training_type)
            elif action.startswith("adjust_"):
                await self._adjust_setting(action, rule)
            else:
                self._log_ui(f"🔧 執行動作：{action}")
                
        except Exception as e:
            self._log_ui(f"⚠️ 執行動作失敗：{e}")
    
    async def _scan_device(self):
        """掃描發球機"""
        try:
            self._log_ui("🔍 開始掃描發球機...")
            if hasattr(self.window, 'scan_devices'):
                await self.window.scan_devices()
            else:
                self._log_ui("⚠️ 掃描功能不可用")
        except Exception as e:
            self._log_ui(f"❌ 掃描失敗：{e}")

    async def _connect_device(self):
        """連接發球機"""
        try:
            self._log_ui("🔗 開始連接發球機...")
            if hasattr(self.window, 'connect_device'):
                await self.window.connect_device()
            else:
                self._log_ui("⚠️ 連接功能不可用")
        except Exception as e:
            self._log_ui(f"❌ 連接失敗：{e}")

    async def _disconnect_device(self):
        """斷開發球機連接"""
        try:
            self._log_ui("❌ 斷開發球機連接...")
            if hasattr(self.window, 'disconnect_device'):
                await self.window.disconnect_device()
            else:
                self._log_ui("⚠️ 斷開功能不可用")
        except Exception as e:
            self._log_ui(f"❌ 斷開失敗：{e}")

    async def _start_training(self):
        """開始訓練"""
        if not hasattr(self.window, 'bluetooth_thread') or not self.window.bluetooth_thread:
            self._log_ui("⚠️ 請先連接發球機")
            return
        
        if not getattr(self.window.bluetooth_thread, 'is_connected', False):
            self._log_ui("⚠️ 發球機未連接")
            return
        
        # 開始基本訓練模式
        self._log_ui("🏸 開始羽球訓練...")
        # 這裡可以調用現有的訓練邏輯
    
    async def _stop_training(self):
        """停止訓練"""
        if hasattr(self.window, 'stop_flag'):
            self.window.stop_flag = True
        self._log_ui("⏹️ 停止訓練")
    
    async def _set_speed(self, speed: str):
        """設定發球速度"""
        speed_map = {
            "fast": "高速",
            "slow": "低速", 
            "medium": "中速"
        }
        self._log_ui(f"⚡ 設定發球速度：{speed_map.get(speed, speed)}")
    
    async def _start_specific_training(self, training_type: str):
        """開始特定類型的訓練"""
        training_map = {
            "front_court": "前場練習",
            "back_court": "後場練習",
            "smash": "殺球練習",
            "drop_shot": "吊球練習",
            "multi_ball": "多球練習",
            "single_ball": "單球練習"
        }
        self._log_ui(f"🎯 開始{training_map.get(training_type, training_type)}")
    
    async def _adjust_setting(self, action: str, rule: dict):
        """調整設定"""
        self._log_ui(f"⚙️ 調整設定：{action}")
    
    def _log_ui(self, message: str):
        """記錄到UI（修復版，支援異步環境）"""
        # 先在終端輸出，確保能看到處理過程
        print(f"[語音控制] {message}")
        
        try:
            # 在異步環境中，使用線程安全的方式更新UI
            import threading
            from PyQt5.QtCore import QTimer
            
            def update_ui():
                try:
                    if hasattr(self.window, "voice_chat_log") and self.window.voice_chat_log is not None:
                        self.window.voice_chat_log.append(message)
                        self.window.voice_chat_log.ensureCursorVisible()
                    elif hasattr(self.window, "text_chat_log") and self.window.text_chat_log is not None:
                        self.window.text_chat_log.append(message)
                        self.window.text_chat_log.ensureCursorVisible()
                    elif hasattr(self.window, "log_message"):
                        self.window.log_message(message)
                except Exception as e:
                    print(f"UI更新失敗：{e}")
            
            # 使用QTimer來確保在主線程中執行UI更新
            try:
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, update_ui)
            except Exception:
                # 如果QTimer不可用，直接調用
                update_ui()
                
        except Exception as e:
            print(f"日誌記錄失敗：{e}")
    
    def _update_status(self, status: str, status_type: str = "processing"):
        """更新狀態顯示"""
        try:
            # 直接在當前線程中更新UI，避免QTimer問題
            if hasattr(self.window, "update_voice_status"):
                try:
                    self.window.update_voice_status(status, status_type)
                except Exception as e:
                    print(f"狀態更新失敗：{e}")
                
        except Exception as e:
            print(f"狀態更新異常：{e}")
    
    def _add_chat_message(self, message: str, message_type: str = "system"):
        """添加聊天訊息"""
        try:
            # 直接在當前線程中更新UI，避免QTimer問題
            if hasattr(self.window, "add_voice_chat_message"):
                try:
                    self.window.add_voice_chat_message(message, message_type)
                except Exception as e:
                    print(f"聊天訊息更新失敗：{e}")
                    # 回退到舊的日誌方法
                    self._log_ui(message)
            else:
                # 回退到舊的日誌方法
                self._log_ui(message)
                
        except Exception as e:
            print(f"聊天訊息更新異常：{e}")
            # 確保至少能在終端看到訊息
            self._log_ui(message)


# === 日誌系統 ===
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

# 輔助函數
def format_reply(template: str, context: dict) -> str:
    """格式化回覆模板"""
    try:
        return template.format(**context)
    except Exception:
        return template  # 缺少變數就用原樣

# 向後相容的函數
def create_voice_control(window, **kwargs):
    """創建語音控制實例（向後相容）"""
    config = VoiceConfig()
    
    # 應用參數
    if 'model_path' in kwargs:
        # 忽略舊的 model_path，使用 Whisper API
        pass
    if 'input_device' in kwargs:
        device = kwargs['input_device']
    else:
        device = None
    
    voice_control = VoiceControlTTS(window, config)
    if device is not None:
        voice_control.set_input_device(device)
    
    return voice_control
