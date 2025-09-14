"""
進階訓練檔案解析器

這個模組負責解析進階訓練配置檔案，提供進階訓練的規格和設定。
"""

from typing import Dict, List, Optional
import os


def map_speed_to_interval(speed_text: str) -> float:
    """
    將速度文字轉換為時間間隔（秒）
    
    Args:
        speed_text: 速度文字（"慢", "正常", "快", "極限快"）
        
    Returns:
        對應的時間間隔（秒）
    """
    speed_mapping = {
        "慢": 4.0,
        "正常": 3.5,
        "快": 2.5,
        "極限快": 1.4
    }
    return speed_mapping.get(speed_text, 3.5)


def parse_ball_count(ball_count_text: str) -> int:
    """
    解析球數文字為數字
    
    Args:
        ball_count_text: 球數文字（"10顆", "20顆", "30顆"）
        
    Returns:
        球數
    """
    ball_count_mapping = {
        "10顆": 10,
        "20顆": 20,
        "30顆": 30
    }
    return ball_count_mapping.get(ball_count_text, 10)


def parse_advance_specs(file_path: str) -> Dict[str, Dict]:
    """
    解析進階訓練配置檔案
    
    Args:
        file_path: 配置檔案路徑
        
    Returns:
        解析後的進階訓練規格字典
        {
            title: {
                "mode": "random" | "sequence",
                "sections": ["secX_1", ...],
                "description": "完整描述文字"
            }
        }
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]
    except Exception:
        return {}

    # 按空行分割區塊
    blocks: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)

    result: Dict[str, Dict] = {}
    for blk in blocks:
        if not blk:
            continue
            
        title = blk[0].strip()
        description = "\n".join(blk).strip()

        mode = None
        sections: List[str] = []
        
        # 尋找「發球點位」下的模式行
        for idx, line in enumerate(blk):
            if line.strip() == "發球點位" and idx + 1 < len(blk):
                next_line = blk[idx + 1].strip()
                if next_line.startswith("隨機發"):
                    mode = "random"
                elif next_line.startswith("依序發"):
                    mode = "sequence"
                # 擷取所有 sec 標記
                tokens = next_line.split()
                sections = [tok for tok in tokens if tok.startswith("sec")]
                break

        if title and mode and sections:
            result[title] = {
                "mode": mode,
                "sections": sections,
                "description": description,
            }

    return result


def load_advanced_training_specs(file_path: str = "adavance_training.txt") -> Dict[str, Dict]:
    """
    載入進階訓練規格
    
    Args:
        file_path: 配置檔案路徑
        
    Returns:
        進階訓練規格字典
    """
    if not os.path.exists(file_path):
        return {}
    
    return parse_advance_specs(file_path)


def get_advanced_training_titles(specs: Dict[str, Dict]) -> List[str]:
    """
    取得所有進階訓練標題
    
    Args:
        specs: 進階訓練規格字典
        
    Returns:
        標題列表
    """
    return list(specs.keys())


def get_advanced_training_description(title: str, specs: Dict[str, Dict]) -> str:
    """
    取得指定進階訓練的描述
    
    Args:
        title: 訓練標題
        specs: 進階訓練規格字典
        
    Returns:
        格式化的描述文字
    """
    spec = specs.get(title, {})
    if not spec:
        return "尚未載入進階訓練內容"
    
    mode_label = "隨機發" if spec.get("mode") == "random" else "依序發"
    sections = " ".join(spec.get("sections", []))
    desc = spec.get("description", title)
    extra = f"\n\n模式: {mode_label}\n發球點位: {sections}"
    
    return desc + extra
