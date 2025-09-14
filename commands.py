import json


# ============================================================================
# 工具函數
# ============================================================================

def read_data_from_json(file_path):
    """從 JSON 文件讀取數據"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"讀取 JSON 文件失敗: {e}")
        return None

def calculate_crc16_modbus(data: bytes) -> int:
    """計算 CRC16 校驗碼"""
    crc = 0xFFFF
    polynomial = 0xA001

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1

    return crc & 0xFFFF

def create_shot_command(speed, horizontal_angle, vertical_angle, height):
    """創建發球指令"""
    data = bytearray([
        speed, horizontal_angle, vertical_angle, height,
        speed, horizontal_angle, vertical_angle, height
    ])
    
    command = bytearray([
        0xAF, 0x13, 0x1A, 0x11, 0x01, 0x00, 0x04, 0x03
    ])
    
    command.extend(data)
    
    crc_data = command[2:]
    crc = calculate_crc16_modbus(crc_data)
    
    command.append(crc & 0xFF)
    command.append((crc >> 8) & 0xFF)
    command.append(0xFA)
    
    return command

def parse_area_params(area_str):
    """解析區域參數字符串"""
    try:
        params = [int(x.strip(), 16) for x in area_str.split(",")]
        if len(params) >= 4:
            return {
                'speed': params[0],
                'horizontal_angle': params[1], 
                'vertical_angle': params[2],
                'height': params[3]
            }
    except Exception as e:
        print(f"解析區域參數失敗: {e}")
    return None
