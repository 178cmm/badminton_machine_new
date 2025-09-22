"""
管理器模組

這個模組包含所有資源和狀態管理功能：
- bluetooth_manager: 藍牙連接管理
- dual_bluetooth_manager: 雙發球機藍牙連接管理
"""

from .bluetooth_manager import create_bluetooth_manager, BluetoothManager
from .dual_bluetooth_manager import create_dual_bluetooth_manager, DualBluetoothManager

__all__ = [
    'create_bluetooth_manager',
    'BluetoothManager',
    'create_dual_bluetooth_manager',
    'DualBluetoothManager'
]
