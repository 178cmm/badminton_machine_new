# 文檔目錄

本目錄包含羽毛球發球機控制系統的詳細文檔與開發說明。

## 專案總覽與雙發球機
- [雙發球機整合指南](DUAL_MACHINE_GUIDE.md) — 單一文件整合架構、操作、協調與故障排除
- （過往文檔保留作歷史參考）

## 功能說明
- [模擬對打模式說明](SIMULATION_MODE_README.md)
- [語音控制整合指南](VOICE_GUIDE.md)
- [系統整合完成說明](INTEGRATION_COMPLETE_README.md)

## 快速上手
1. 先閱讀主目錄的 [README.md](../README.md) 了解系統概述與安裝
2. 在 GUI 連接頁選擇「雙發球機」，掃描並連接左右發球機
3. 在「手動控制」頁的「雙發球機」子頁，選擇目標（左/右/協調）與模式測試發球

## 開發者指南
- GUI 子頁結構：`ui_connection.py`（連接）、`ui_control.py`（手動控制：已拆單/雙子頁）
- 管理器：`core/managers/dual_bluetooth_manager.py`、`dual_bluetooth_thread.py`
- 協調邏輯：`DualMachineCoordinator`（同時/交替/序列，支援 interval、count）

## 更新記錄
- 2025-09-18: 手動控制頁拆分為單/雙子頁，加入協調參數
- 2025-09-18: 雙機協調 API 新增 interval、count 參數
- 2024-09-18: 整理文檔索引與架構說明
