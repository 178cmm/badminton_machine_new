# 雙發球機整合指南

本文件整合了雙發球機的架構、實作進度、使用方式與故障排除，取代分散的多份說明。

## 1. 概述
- 目標：在現有單發球機基礎上，支援同時管理兩台發球機，提供交替/同時/序列等協調模式。
- 狀態：第一階段（雙設備掃描/識別/連接）已完成；第二階段（協調控制）進行中。

## 2. 核心架構
- 管理器：`core/managers/dual_bluetooth_manager.py`
- 線程與協調：`core/managers/dual_bluetooth_thread.py`（含 `DualMachineCoordinator`）
- GUI：
  - 連接頁：`gui/ui_connection.py`（單/雙子頁）
  - 手動控制：`gui/ui_control.py`（已拆成單/雙子頁，雙子頁含協調參數）

## 3. 功能與 API
- 連接流程：
  - 掃描：`DualBluetoothManager.scan_dual_devices()`
  - 連接：`DualBluetoothManager.connect_dual_machines()`
  - 斷開：`DualBluetoothManager.disconnect_dual_machines()`
  - 狀態：`DualBluetoothManager.is_dual_connected()`
- 協調發球：
  - `DualBluetoothManager.send_coordinated_shot(left_area, right_area, coordination_mode, interval=0.5, count=1)`
  - 模式：`alternate`（交替）、`simultaneous`（同時）、`sequence`（序列）
  - 參數：`interval`（交替/序列用）、`count`（重複次數）
- 每台機器的冷卻：`DualBluetoothThread.shot_cooldown`（預設 0.5s）

## 4. GUI 操作
- 連接頁「雙發球機」子頁：掃描、左右選擇、連接/斷開、狀態顯示。
- 手動控制頁：
  - 單機子頁：單發/連發、球數、間隔、區域按鍵（走 `bluetooth_thread`）。
  - 雙機子頁：目標（左/右/協調），協調模式/間隔/次數；或左右單機連發的球數/間隔。

## 5. 開發階段
- 第一階段（已完成）：雙設備掃描/識別/連接、UI 擴展、監控與錯誤處理。
- 第二階段（進行中）：協調控制（alternate/simultaneous/sequence），時間精度與參數化。
- 第三階段（規劃）：進階訓練、數據分析、體驗優化等。

## 6. 故障排除（重點彙整）
- 無法掃描到設備：確認藍牙權限與 `bleak` 正常；設備名稱需以 `YX-BE241` 開頭。
- 左右識別錯誤：可於掃描後手動重新分配；或檢查 MAC 尾碼奇偶規則。
- 連接按鈕無反應：確保左右皆已選擇且非同一地址；查看日誌輸出與 GUI 狀態標籤。
- 協調發球不同步：調整 `interval` 與 `sync_tolerance`；避免將 `interval` 設過小低於 BLE 寫入延遲。

## 7. 測試與調試
- 雙機測試：`test_dual_machine.py`（含協調發球範例）
- 分配測試：`test_device_assignment.py`
- 工作流：`test_full_workflow.py`
- 調試腳本：`debug_connection.py`、`debug_dual_scan.py`

## 8. 建議參數與極限
- 交替高頻：`mode=alternate`，`interval≈0.25~0.35s` 視硬體穩定度微調。
- 同時發球：`mode=simultaneous`，關注日誌中的同步容差提示。

## 9. 變更記錄（摘要）
- 2025-09-18：手動控制拆單/雙子頁，協調 API 支援 `interval`/`count`。
- 2024-09-18：完成第一階段與文件初版。

---
維護者：開發團隊
