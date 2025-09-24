"""
回覆模板集中管理
"""

from typing import Callable


class ReplyTemplates:
    # 固定文案
    WAKE_OK = "彥澤您好，我是你的智慧發球機助理，請下達指令"
    SCAN_START = "正在掃描發球機"
    CONNECT_START = "正在連線發球機"
    CONNECT_DONE = "連線成功，今天想要練什麼呢"
    DISCONNECT_START = "正在斷開連線"
    DISCONNECT_DONE = "正在斷開連線，期待下次再一起訓練"

    @staticmethod
    def SCAN_DONE(n: int) -> str:
        return f"掃描成功，偵測到 {n} 台裝置"

    # 訓練相關
    @staticmethod
    def PROGRAM_START(program_name: str, balls: float, interval_sec: float) -> str:
        return f"開始『{program_name}』：共 {int(balls)} 顆、每球 {interval_sec} 秒"
    
    @staticmethod
    def INDIVIDUAL_SHOT_START(name: str, balls: float, interval_sec: float) -> str:
        return f"開始單一球路『{name}』：共 {int(balls)} 顆、每球 {interval_sec} 秒"

    PROGRAM_DONE = "本次訓練完成，辛苦了！"

    @staticmethod
    def PROGRAM_MULTI(candidates: list[str]) -> str:
        joined = "、".join(candidates)
        return f"我找到多個相近的訓練：{joined}，請再說一次或選擇一個"

    PROGRAM_NOT_FOUND = "抱歉，找不到對應的訓練名稱，請再試一次"
    NOT_FOUND = PROGRAM_NOT_FOUND
    NOT_CONNECTED = "目前尚未連線到發球機，請先說『連線』或點擊連線按鈕"

    # 別名 for parser/router 用語一致性
    @staticmethod
    def ASK_DISAMBIGUATION(cands: list[str]) -> str:
        return ReplyTemplates.PROGRAM_MULTI(cands)

    # 語音限制
    PROGRAM_VOICE_DISABLED = "課程訓練僅支援手動操作，請改用手動控制介面"


