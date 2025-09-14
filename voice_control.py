import asyncio
import json
import re
import sys
import shutil
from typing import Optional, List

try:
    from vosk import Model, KaldiRecognizer
except Exception:  # pragma: no cover - 避免未安裝時直接崩潰
    Model = None  # type: ignore
    KaldiRecognizer = None  # type: ignore

try:
    import sounddevice as sd
except Exception:  # pragma: no cover
    sd = None  # type: ignore


SHOT_NAMES: List[str] = [
    "正手高遠球", "反手高遠球",
    "正手切球", "反手切球",
    "正手殺球", "反手殺球",
    "正手平抽球", "反手平抽球",
    "正手小球", "反手小球",
    "正手挑球", "反手挑球",
    "平推球",
    "正手接殺球", "反手接殺球",
    "近身接殺",
]

_TRAD_TO_SIMP = {
    "遠": "远",
    "顆": "颗",
    "殺": "杀",
    "間": "间",
}

def to_simplified(text: str) -> str:
    return "".join(_TRAD_TO_SIMP.get(ch, ch) for ch in text)

def to_traditional(text: str) -> str:
    inv = {v: k for k, v in _TRAD_TO_SIMP.items()}
    return "".join(inv.get(ch, ch) for ch in text)


class VoiceControl:
    """
    以 Vosk + Grammar 實作的語音控制。
    - 非同步監聽麥克風，不阻塞 PyQt5 + qasync 主執行緒
    - Grammar 僅允許：球種名稱、數字 1~100、「顆」「間隔」「秒」關鍵字
    - 解析完成後，直接呼叫現有發球流程（透過 window.bluetooth_thread / send_shot）
    - 於 UI 的 `text_chat_log` 顯示最後一次辨識與解析結果（若存在）
    """

    def __init__(self, window, model_path: str = "models/vosk-model-small-cn-0.22", samplerate: int = 16000, input_device: Optional[int] = None, use_grammar: bool = False, backend: str = "auto", ffmpeg_audio_index: Optional[int] = None):
        self.window = window
        self.model_path = model_path
        self.samplerate = samplerate
        self.input_device = input_device
        self.use_grammar = use_grammar
        self.backend = backend  # auto | sounddevice | ffmpeg
        self.ffmpeg_audio_index = ffmpeg_audio_index if ffmpeg_audio_index is not None else 0

        self._model = None
        self._recognizer = None
        self._audio_stream = None
        self._running = False
        self._starting = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._listen_task: Optional[asyncio.Task] = None
        self._execute_task: Optional[asyncio.Task] = None
        self._capture_task: Optional[asyncio.Task] = None
        self._start_stop_lock = asyncio.Lock()
        self._sentence_buffer: str = ""
        self._last_sentence_ts: float = 0.0
        self._ffmpeg_process = None
        self._audio_seen_logged = False

        # 構建 Grammar 字彙
        self._grammar_words = self._build_grammar_words()

    def _build_grammar_words(self) -> List[str]:
        words: List[str] = []
        # 僅使用簡體單字，避免 small-cn 模型 OOV（忽略繁體單字）
        charset = set()
        for name in SHOT_NAMES:
            for ch in to_simplified(name):
                charset.add(ch)
        for ch in ["颗", "秒", "间", "隔", "高", "远", "手", "反", "正", "球", "接", "杀", "平", "抽", "挑", "近", "身", "切"]:
            charset.add(ch)
        for ch in ["零", "〇", "一", "二", "两", "三", "四", "五", "六", "七", "八", "九", "十", "百"]:
            charset.add(ch)
        for d in "0123456789":
            charset.add(d)
        words.extend(sorted(charset))
        
        # 去重
        seen = set()
        deduped = []
        for w in words:
            if w not in seen:
                seen.add(w)
                deduped.append(w)
        return deduped

    async def start(self):
        """啟動語音監聽。"""
        # 防重入與競態
        if self._running or self._starting:
            return
        async with self._start_stop_lock:
            if self._running or self._starting:
                return
            self._starting = True
        # 載入模型
        if Model is None or KaldiRecognizer is None:
            self._log_ui("未安裝 vosk，請先在環境中安裝 vosk 套件。")
            self._starting = False
            return
        if sd is None and self.backend in ("auto", "sounddevice"):
            self._log_ui("未安裝 sounddevice，請先在環境中安裝 sounddevice 套件或切換到 ffmpeg 後端。")
            self._starting = False
            return

        # 基本路徑檢查與提示
        import os
        if not os.path.isdir(self.model_path):
            self._log_ui(
                f"找不到 Vosk 模型資料夾：{self.model_path}\n"
                "請先下載並解壓官方中文模型（建議 small-cn-0.22），\n"
                "將整個資料夾置於上述路徑，或在啟動時提供正確的 model_path，\n"
                "或設定環境變數 VOSK_MODEL_PATH 指向模型資料夾。\n"
                "下載頁面：" + "https://alphacephei.com/vosk/models"
            )
            self._starting = False
            return

        try:
            self._model = Model(self.model_path)
        except Exception as e:
            self._log_ui(f"載入 Vosk 模型失敗：{e}")
            self._starting = False
            return

        if self.use_grammar:
            grammar_json = json.dumps(self._grammar_words, ensure_ascii=False)
            self._recognizer = KaldiRecognizer(self._model, self.samplerate, grammar_json)
        else:
            self._recognizer = KaldiRecognizer(self._model, self.samplerate)

        # 選擇音訊後端
        # macOS 預設優先使用 sounddevice，避免 ffmpeg 權限/裝置索引問題
        chosen_backend = self.backend
        if chosen_backend == "auto":
            chosen_backend = "sounddevice"
        self._log_ui(f"音訊後端：{chosen_backend}，採樣率：{self.samplerate}，裝置：{self.input_device if self.input_device is not None else 'default'}")

        if chosen_backend == "sounddevice":
            try:
                stream_kwargs = dict(
                    samplerate=self.samplerate,
                    blocksize=8000,
                    dtype="int16",
                    channels=1,
                )
                if self.input_device is not None:
                    stream_kwargs["device"] = self.input_device
                self._audio_stream = sd.RawInputStream(**stream_kwargs)
                self._audio_stream.start()
            except Exception as e:
                self._log_ui(f"開啟麥克風失敗（sounddevice）：{e}，嘗試以 ffmpeg 後端重試…")
                # 立即嘗試回退到 ffmpeg
                chosen_backend = "ffmpeg"
            else:
                self._running = True
                self._capture_task = asyncio.create_task(self._capture_loop())
        else:
            # 使用 ffmpeg 後端（macOS: avfoundation）
            if sys.platform == "darwin":
                cmd = [
                    "ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-f", "avfoundation",
                    "-i", f":{int(self.ffmpeg_audio_index)}",
                    "-ac", "1",
                    "-ar", str(int(self.samplerate)),
                    "-f", "s16le", "-",
                ]
            else:
                # 其他平台可視需求擴充（預設嘗試 default）
                cmd = [
                    "ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-f", "alsa" if sys.platform.startswith("linux") else "dshow",
                    "-i", "default" if sys.platform.startswith("linux") else "audio=default",
                    "-ac", "1",
                    "-ar", str(int(self.samplerate)),
                    "-f", "s16le", "-",
                ]
            try:
                self._ffmpeg_process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
            except Exception as e:
                self._log_ui(f"啟動 ffmpeg 失敗：{e}，改用 sounddevice 後端重試。")
                # fallback to sounddevice
                try:
                    if sd is None:
                        raise RuntimeError("sounddevice 未安裝")
                    stream_kwargs = dict(
                        samplerate=self.samplerate,
                        blocksize=8000,
                        dtype="int16",
                        channels=1,
                    )
                    if self.input_device is not None:
                        stream_kwargs["device"] = self.input_device
                    self._audio_stream = sd.RawInputStream(**stream_kwargs)
                    self._audio_stream.start()
                    self._running = True
                    self._capture_task = asyncio.create_task(self._capture_loop())
                except Exception as e2:
                    self._log_ui(f"sounddevice 後端也啟動失敗：{e2}")
                    self._starting = False
                    return
            if not self._audio_stream:
                self._running = True
                self._capture_task = asyncio.create_task(self._ffmpeg_capture_loop())

        self._listen_task = asyncio.create_task(self._listen_loop())
        self._log_ui("語音控制：已啟動，請說出指令，例如『正手高遠球 20 顆 間隔 3 秒』。")
        self._starting = False

    async def stop(self):
        """停止語音監聽並釋放資源。"""
        async with self._start_stop_lock:
            if not self._running and not self._starting:
                return
            # 將 starting 狀態也一併中止
            self._starting = False
        self._running = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self._listen_task = None

        if self._capture_task and not self._capture_task.done():
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
        self._capture_task = None

        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
                self._audio_stream.close()
            except Exception:
                pass
            self._audio_stream = None
        if self._ffmpeg_process is not None:
            try:
                self._ffmpeg_process.terminate()
            except Exception:
                pass
            self._ffmpeg_process = None

        # 停止任何仍在執行的發球任務
        if self._execute_task and not self._execute_task.done():
            self._execute_task.cancel()
            try:
                await self._execute_task
            except asyncio.CancelledError:
                pass
        self._execute_task = None

        self._log_ui("語音控制：已停止。")

    async def _capture_loop(self):
        # 以阻塞讀的方式從 PortAudio 擷取資料，避免使用 Python callback（cffi）
        while self._running and self._audio_stream is not None:
            try:
                # 將阻塞 I/O 丟到背景執行緒，避免卡住事件圈
                loop = asyncio.get_running_loop()
                data, _overflowed = await loop.run_in_executor(None, self._audio_stream.read, 8000)
                if data:
                    try:
                        if not self._audio_seen_logged:
                            self._audio_seen_logged = True
                            self._log_ui("已開始接收麥克風音訊…")
                        self._audio_queue.put_nowait(bytes(data))
                    except Exception:
                        pass
            except asyncio.CancelledError:
                break
            except Exception:
                # 讀取錯誤時稍作延遲避免忙等
                await asyncio.sleep(0.01)

    async def _ffmpeg_capture_loop(self):
        if not self._ffmpeg_process or not self._ffmpeg_process.stdout:
            return
        while self._running:
            try:
                chunk = await self._ffmpeg_process.stdout.read(8000)
                if not chunk:
                    await asyncio.sleep(0.01)
                    continue
                try:
                    if not self._audio_seen_logged:
                        self._audio_seen_logged = True
                        self._log_ui("已開始接收麥克風音訊（ffmpeg）…")
                    self._audio_queue.put_nowait(bytes(chunk))
                except Exception:
                    pass
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.01)

    def _on_audio(self, indata, frames, time, status):  # sounddevice callback（執行於非 asyncio 執行緒）
        if not self._running:
            return
        if status:
            # 可視需要輸出狀態
            pass
        try:
            # 將 bytes 丟入 asyncio 隊列
            self._audio_queue.put_nowait(bytes(indata))
        except Exception:
            pass

    async def _listen_loop(self):
        assert self._recognizer is not None
        while self._running:
            try:
                data = await self._audio_queue.get()
            except asyncio.CancelledError:
                break
            if not data:
                continue
            try:
                if self._recognizer.AcceptWaveform(data):
                    result_json = self._recognizer.Result()
                    self._handle_result_json(result_json)
                else:
                    # 顯示 partial 結果以便除錯
                    try:
                        pj = json.loads(self._recognizer.PartialResult() or "{}")
                        partial = (pj.get("partial") or "").strip()
                        if partial:
                            self._log_ui(f"（部分）{partial}")
                    except Exception:
                        pass
            except Exception:
                # 保護性處理，避免 recognizer 崩潰
                continue

    def _handle_result_json(self, result_json: str):
        try:
            obj = json.loads(result_json)
        except Exception:
            return
        text = (obj.get("text") or "").strip()
        if not text:
            return
        # 顯示原始辨識文本
        self._log_ui(f"語音：{text}")

        # 解析（僅允許 Grammar 字彙，結構：<球種> [<數字> 顆] [間隔 <數字> 秒]）
        # 正規化：移除空白、簡轉繁
        normalized = to_traditional(text.replace(" ", ""))
        parsed = self._parse_command_from_text(normalized)
        if not parsed:
            self._log_ui("（無法解析為有效指令）")
            return

        self._log_ui(f"解析：{parsed}")
        
        # 處理模擬對打指令
        if parsed.get("type") == "start_simulation":
            self._execute_simulation_command(parsed)
        elif parsed.get("type") == "stop_simulation":
            self._execute_stop_simulation_command()
        else:
            # 啟動非阻塞的發球流程（避免與既有訓練衝突，只送指定顆數）
            if self._execute_task and not self._execute_task.done():
                self._execute_task.cancel()
            self._execute_task = asyncio.create_task(self._execute_specific_shot(parsed["shot_name"], parsed["count"], parsed["interval"]))

    def _parse_command_from_text(self, text: str) -> Optional[dict]:
        # 首先檢查是否為模擬對打指令
        simulation_result = self._parse_simulation_command(text)
        if simulation_result:
            return simulation_result
        
        # 找球種（以包含關鍵片段為準）
        shot_name = None
        for name in SHOT_NAMES:
            if name in text:
                shot_name = name
                break
        if not shot_name:
            return None

        # 數量（預設 10 顆）。先抓阿拉伯數字，再抓中文數字
        count = self._extract_first_int_in_range(text, 1, 100)
        if count is None:
            count = self._extract_first_cn_number(text)
        if count is None:
            count = 10

        # 間隔秒數（預設 5 秒）
        interval = self._extract_interval_seconds(text)
        if interval is None:
            interval = 5.0

        return {"shot_name": shot_name, "count": int(count), "interval": float(interval)}

    def _parse_simulation_command(self, text: str) -> Optional[dict]:
        """解析模擬對打指令"""
        # 模擬對打關鍵字
        simulation_keywords = ["模擬對打", "對打模式", "對打", "模擬", "對戰", "對練"]
        
        # 檢查是否包含模擬對打關鍵字
        if not any(keyword in text for keyword in simulation_keywords):
            return None
        
        # 檢查是否為停止指令
        stop_keywords = ["停止", "結束", "暫停"]
        if any(keyword in text for keyword in stop_keywords):
            return {"type": "stop_simulation"}
        
        # 提取等級
        level = self._extract_simulation_level(text)
        if level is None:
            level = 1  # 預設等級
        
        # 檢查是否使用雙發球機
        dual_keywords = ["雙發球機", "兩台", "雙機", "雙球機", "兩台發球機"]
        use_dual = any(keyword in text for keyword in dual_keywords)
        
        return {
            "type": "start_simulation",
            "level": level,
            "use_dual_machine": use_dual
        }
    
    def _extract_simulation_level(self, text: str) -> Optional[int]:
        """提取模擬對打等級"""
        # 直接匹配數字
        level = self._extract_first_int_in_range(text, 1, 12)
        if level:
            return level
        
        # 匹配中文數字
        cn_level = self._extract_first_cn_number(text)
        if cn_level and 1 <= cn_level <= 12:
            return cn_level
        
        # 匹配等級關鍵字
        level_keywords = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12
        }
        
        for keyword, level in level_keywords.items():
            if keyword in text:
                return level
        
        return None

    def _execute_simulation_command(self, parsed: dict):
        """執行模擬對打指令"""
        try:
            level = parsed.get("level", 1)
            use_dual = parsed.get("use_dual_machine", False)
            
            self._log_ui(f"開始模擬對打 - 等級 {level}" + (" (雙發球機)" if use_dual else ""))
            
            # 創建模擬對打執行器
            if not hasattr(self.window, 'simulation_executor'):
                from core.executors.simulation_executor import create_simulation_executor
                self.window.simulation_executor = create_simulation_executor(self.window)
            
            # 開始模擬對打
            success = self.window.simulation_executor.start_simulation(level, use_dual)
            
            if success:
                self._log_ui(f"✅ 模擬對打已開始 - 等級 {level}")
            else:
                self._log_ui("❌ 開始模擬對打失敗")
                
        except Exception as e:
            self._log_ui(f"❌ 執行模擬對打指令時發生錯誤: {e}")
    
    def _execute_stop_simulation_command(self):
        """執行停止模擬對打指令"""
        try:
            self._log_ui("停止模擬對打")
            
            if hasattr(self.window, 'simulation_executor'):
                success = self.window.simulation_executor.stop_simulation()
                
                if success:
                    self._log_ui("✅ 模擬對打已停止")
                else:
                    self._log_ui("❌ 停止模擬對打失敗")
            else:
                self._log_ui("❌ 沒有正在運行的模擬對打")
                
        except Exception as e:
            self._log_ui(f"❌ 停止模擬對打時發生錯誤: {e}")

    @staticmethod
    def _extract_first_int_in_range(text: str, min_v: int, max_v: int) -> Optional[int]:
        # 尋找第一個 1~100 的整數（空白或無空白都可，由於中文輸出常為以空白分詞）
        num = None
        token = ""
        for ch in text:
            if ch.isdigit():
                token += ch
            else:
                if token:
                    try:
                        n = int(token)
                        if min_v <= n <= max_v:
                            num = n
                            break
                    except Exception:
                        pass
                    token = ""
        if num is None and token:
            try:
                n = int(token)
                if min_v <= n <= max_v:
                    num = n
            except Exception:
                pass
        return num

    @staticmethod
    def _extract_interval_seconds(text: str) -> Optional[float]:
        # 嘗試尋找「間隔 X 秒」或結尾的「X 秒」
        # 為避免引入 re，使用簡單字串處理
        if ("間隔" in text or "间隔" in text) and "秒" in text:
            try:
                after = text.split("間隔", 1)[1] if "間隔" in text else text.split("间隔", 1)[1]
                segment = after.split("秒", 1)[0]
                # 在 segment 中抓第一個數字
                token = ""
                for ch in segment:
                    if ch.isdigit() or ch == ".":
                        token += ch
                    elif token:
                        break
                if token:
                    return float(token)
            except Exception:
                pass
            # 嘗試中文數字
            try:
                after = text.split("間隔", 1)[1] if "間隔" in text else text.split("间隔", 1)[1]
                segment = after.split("秒", 1)[0]
                val = VoiceControl._parse_cn_numeral(segment)
                if val:
                    return float(val)
            except Exception:
                pass
        # 後備：任何「X 秒」
        if "秒" in text:
            try:
                segment = text.split("秒", 1)[0]
                token = ""
                for ch in reversed(segment):
                    if ch.isdigit() or ch == ".":
                        token = ch + token
                    elif token:
                        break
                if token:
                    return float(token)
            except Exception:
                pass
            # 中文數字
            try:
                segment = text.split("秒", 1)[0]
                # 取結尾連續中文數字
                m = re.search(r"([零〇○一二兩两三四五六七八九十百]+)$", segment)
                if m:
                    val = VoiceControl._parse_cn_numeral(m.group(1))
                    if val:
                        return float(val)
            except Exception:
                pass
        return None

    @staticmethod
    def _parse_cn_numeral(token: str) -> Optional[int]:
        token = (token or "").strip()
        if not token:
            return None
        cn_map = {"零":0, "〇":0, "○":0, "一":1, "二":2, "兩":2, "两":2, "三":3, "四":4, "五":5, "六":6, "七":7, "八":8, "九":9}
        # 簡單支援到 100
        if token == "十":
            return 10
        if token == "百":
            return 100
        # X十Y / X十 / 十Y
        if "十" in token:
            parts = token.split("十")
            if len(parts) == 2:
                left, right = parts
                left_val = cn_map.get(left, 1) if left != "" else 1
                right_val = cn_map.get(right, 0) if right != "" else 0
                return left_val * 10 + right_val
        # 單字
        if token in cn_map:
            return cn_map[token]
        # 其他形式略過
        return None

    @staticmethod
    def _extract_first_cn_number(text: str) -> Optional[int]:
        m = re.search(r"([零〇○一二兩两三四五六七八九十百]{1,3})(顆|颗|球|次)?", text)
        if m:
            return VoiceControl._parse_cn_numeral(m.group(1))
        return None

    async def _execute_specific_shot(self, shot_name: str, count: int, interval: float):
        # 透過既有的 mapping 取得 section
        try:
            section = self.window.get_section_by_shot_name(shot_name)
        except Exception:
            section = None
        if not section:
            self._log_ui(f"找不到球種對應：{shot_name}")
            return

        if not getattr(self.window, "bluetooth_thread", None):
            self._log_ui("請先掃描並連接發球機。")
            return
        if not getattr(self.window.bluetooth_thread, "is_connected", False):
            self._log_ui("請先連接發球機。")
            return

        sent = 0
        try:
            for _ in range(count):
                # 若外部在進行訓練，避免互相干擾
                if getattr(self.window, "stop_flag", False):
                    self._log_ui("偵測到停止旗標，終止語音發球流程。")
                    break
                try:
                    await self.window.bluetooth_thread.send_shot(section)
                except Exception as e:
                    self._log_ui(f"發球失敗：{e}")
                    break
                sent += 1
                self._log_ui(f"語音發球：{shot_name} 第 {sent} 顆（{section}）")
                await asyncio.sleep(max(0.2, float(interval)))
        finally:
            self._log_ui(f"語音發球完成：{shot_name} 共 {sent}/{count} 顆。")

    def _log_ui(self, message: str):
        # 優先寫入語音控制頁；其次文本控制；否則退回系統日誌
        try:
            if hasattr(self.window, "voice_chat_log") and self.window.voice_chat_log is not None:
                self.window.voice_chat_log.append(message)
                self.window.voice_chat_log.ensureCursorVisible()
            elif hasattr(self.window, "text_chat_log") and self.window.text_chat_log is not None:
                self.window.text_chat_log.append(message)
                self.window.text_chat_log.ensureCursorVisible()
            elif hasattr(self.window, "log_message"):
                self.window.log_message(message)
        except Exception:
            pass

