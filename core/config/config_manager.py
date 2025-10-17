"""
統一配置管理器

這個模組負責統一管理所有訓練配置，提供統一的 API 供各模組使用。
支援配置的動態載入和重新載入。
"""

import json
import os
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime


class ConfigManager:
    """統一配置管理器類別"""
    
    def __init__(self, config_root: str = "config"):
        """
        初始化配置管理器
        
        Args:
            config_root: 配置檔案根目錄
        """
        self.config_root = config_root
        self._cache = {}
        self._file_timestamps = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """載入所有配置檔案"""
        # 載入訓練配置
        self._load_training_configs()
        
        # 載入 NLU 配置
        self._load_nlu_configs()
        
        # 載入系統配置
        self._load_system_configs()
    
    def _load_training_configs(self):
        """載入訓練相關配置"""
        training_dir = os.path.join(self.config_root, "training")
        
        # 載入基礎訓練和課程配置（向後相容）
        programs_file = os.path.join(training_dir, "programs.json")
        if os.path.exists(programs_file):
            self._cache["programs"] = self._load_json_file(programs_file)
        
        # 載入基礎訓練配置
        basic_training_file = os.path.join(training_dir, "basic_training.json")
        if os.path.exists(basic_training_file):
            self._cache["basic_training"] = self._load_json_file(basic_training_file)
        
        # 載入課程訓練配置
        course_training_file = os.path.join(training_dir, "course_training.json")
        if os.path.exists(course_training_file):
            self._cache["course_training"] = self._load_json_file(course_training_file)
        
        # 載入熱身配置
        warmup_file = os.path.join(training_dir, "warmup.json")
        if os.path.exists(warmup_file):
            self._cache["warmup"] = self._load_json_file(warmup_file)
        
        # 載入進階訓練配置
        advanced_file = os.path.join(training_dir, "advanced.json")
        if os.path.exists(advanced_file):
            self._cache["advanced"] = self._load_json_file(advanced_file)
        
        # 載入球路描述配置
        shots_dir = os.path.join(training_dir, "shots")
        if os.path.exists(shots_dir):
            self._cache["shots"] = {}
            for filename in os.listdir(shots_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(shots_dir, filename)
                    config_name = filename[:-5]  # 移除 .json 副檔名
                    self._cache["shots"][config_name] = self._load_json_file(filepath)
    
    def _load_nlu_configs(self):
        """載入 NLU 相關配置"""
        nlu_dir = os.path.join(self.config_root, "nlu")
        
        if os.path.exists(nlu_dir):
            self._cache["nlu"] = {}
            for filename in os.listdir(nlu_dir):
                if filename.endswith(('.yaml', '.yml')):
                    filepath = os.path.join(nlu_dir, filename)
                    config_name = filename.split('.')[0]
                    self._cache["nlu"][config_name] = self._load_yaml_file(filepath)
    
    def _load_system_configs(self):
        """載入系統相關配置"""
        system_dir = os.path.join(self.config_root, "system")
        
        if os.path.exists(system_dir):
            self._cache["system"] = {}
            for filename in os.listdir(system_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(system_dir, filename)
                    config_name = filename[:-5]  # 移除 .json 副檔名
                    self._cache["system"][config_name] = self._load_json_file(filepath)
    
    def _load_json_file(self, filepath: str) -> Dict[str, Any]:
        """載入 JSON 檔案"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._file_timestamps[filepath] = os.path.getmtime(filepath)
            return data
        except Exception as e:
            print(f"載入 JSON 檔案失敗 {filepath}: {e}")
            return {}
    
    def _load_yaml_file(self, filepath: str) -> Dict[str, Any]:
        """載入 YAML 檔案"""
        try:
            import yaml
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self._file_timestamps[filepath] = os.path.getmtime(filepath)
            return data
        except Exception as e:
            print(f"載入 YAML 檔案失敗 {filepath}: {e}")
            return {}
    
    def reload_config(self, config_type: str = None):
        """
        重新載入配置
        
        Args:
            config_type: 配置類型，如果為 None 則重新載入所有配置
        """
        if config_type is None:
            self._cache.clear()
            self._file_timestamps.clear()
            self._load_all_configs()
        elif config_type == "training":
            self._cache.pop("programs", None)
            self._cache.pop("basic_training", None)
            self._cache.pop("course_training", None)
            self._cache.pop("warmup", None)
            self._cache.pop("advanced", None)
            self._cache.pop("shots", None)
            self._load_training_configs()
        elif config_type == "nlu":
            self._cache.pop("nlu", None)
            self._load_nlu_configs()
        elif config_type == "system":
            self._cache.pop("system", None)
            self._load_system_configs()
    
    def check_and_reload_if_changed(self):
        """檢查檔案是否有變更，如果有則重新載入"""
        for filepath, timestamp in self._file_timestamps.items():
            if os.path.exists(filepath):
                current_timestamp = os.path.getmtime(filepath)
                if current_timestamp > timestamp:
                    # 檔案有變更，重新載入
                    self.reload_config()
                    break
    
    # 訓練配置相關方法
    def get_programs(self) -> Dict[str, Any]:
        """取得基礎訓練和課程配置（向後相容）"""
        return self._cache.get("programs", {})
    
    def get_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        """取得特定訓練套餐（向後相容）"""
        programs = self.get_programs()
        return programs.get("training_programs", {}).get(program_id)
    
    def get_basic_training_configs(self) -> Dict[str, Any]:
        """取得基礎訓練配置"""
        return self._cache.get("basic_training", {})
    
    def get_basic_training_config(self, training_id: str) -> Optional[Dict[str, Any]]:
        """取得特定基礎訓練配置"""
        basic_configs = self.get_basic_training_configs()
        return basic_configs.get("categories", {}).get(training_id)
    
    def get_course_training_configs(self) -> Dict[str, Any]:
        """取得課程訓練配置"""
        return self._cache.get("course_training", {})
    
    def get_course_training_config(self, course_id: str) -> Optional[Dict[str, Any]]:
        """取得特定課程訓練配置"""
        course_configs = self.get_course_training_configs()
        return course_configs.get("categories", {}).get(course_id)
    
    def get_all_course_levels(self) -> List[Dict[str, Any]]:
        """取得所有課程等級"""
        course_configs = self.get_course_training_configs()
        categories = course_configs.get("categories", {})
        
        # 按等級排序
        levels = []
        for course_id, course_data in categories.items():
            level = course_data.get("level", 0)
            levels.append({
                "id": course_id,
                "level": level,
                "name": course_data.get("name", ""),
                "description": course_data.get("description", ""),
                "difficulty": course_data.get("difficulty", ""),
                "duration_minutes": course_data.get("duration_minutes", 0)
            })
        
        return sorted(levels, key=lambda x: x["level"])
    
    def get_warmup_configs(self) -> Dict[str, Any]:
        """取得熱身配置"""
        return self._cache.get("warmup", {})
    
    def get_warmup_config(self, warmup_type: str) -> Optional[Dict[str, Any]]:
        """取得特定熱身配置"""
        warmup_configs = self.get_warmup_configs()
        return warmup_configs.get("categories", {}).get(warmup_type)
    
    def get_advanced_configs(self) -> Dict[str, Any]:
        """取得進階訓練配置"""
        return self._cache.get("advanced", {})
    
    def get_advanced_config(self, advanced_type: str) -> Optional[Dict[str, Any]]:
        """取得特定進階訓練配置"""
        advanced_configs = self.get_advanced_configs()
        return advanced_configs.get("categories", {}).get(advanced_type)
    
    def get_shot_descriptions(self) -> Dict[str, Any]:
        """取得球路描述配置"""
        return self._cache.get("shots", {})
    
    def get_shot_description(self, shot_name: str) -> Optional[Dict[str, Any]]:
        """取得特定球路描述"""
        shots = self.get_shot_descriptions()
        for config_name, config_data in shots.items():
            shots_data = config_data.get("shots", {})
            if shot_name in shots_data:
                return shots_data[shot_name]
        return None
    
    # NLU 配置相關方法
    def get_nlu_configs(self) -> Dict[str, Any]:
        """取得 NLU 配置"""
        return self._cache.get("nlu", {})
    
    def get_aliases(self) -> Dict[str, Any]:
        """取得同義詞配置"""
        nlu_configs = self.get_nlu_configs()
        return nlu_configs.get("aliases", {})
    
    def get_suffixes(self) -> Dict[str, Any]:
        """取得尾綴規則配置"""
        nlu_configs = self.get_nlu_configs()
        return nlu_configs.get("suffixes", {})
    
    # 系統配置相關方法
    def get_system_configs(self) -> Dict[str, Any]:
        """取得系統配置"""
        return self._cache.get("system", {})
    
    # 便利方法
    def get_all_training_types(self) -> List[str]:
        """取得所有訓練類型"""
        types = []
        
        # 基礎訓練和課程（向後相容）
        programs = self.get_programs()
        if "training_programs" in programs:
            types.extend(programs["training_programs"].keys())
        
        # 基礎訓練
        basic_configs = self.get_basic_training_configs()
        if "categories" in basic_configs:
            types.extend([f"basic_{k}" for k in basic_configs["categories"].keys()])
        
        # 課程訓練
        course_configs = self.get_course_training_configs()
        if "categories" in course_configs:
            types.extend([f"course_{k}" for k in course_configs["categories"].keys()])
        
        # 熱身
        warmup_configs = self.get_warmup_configs()
        if "categories" in warmup_configs:
            types.extend([f"warmup_{k}" for k in warmup_configs["categories"].keys()])
        
        # 進階訓練
        advanced_configs = self.get_advanced_configs()
        if "categories" in advanced_configs:
            types.extend([f"advanced_{k}" for k in advanced_configs["categories"].keys()])
        
        return types
    
    def search_training_by_name(self, name: str) -> List[Dict[str, Any]]:
        """根據名稱搜尋訓練配置"""
        results = []
        name_lower = name.lower()
        
        # 搜尋基礎訓練和課程（向後相容）
        programs = self.get_programs()
        if "training_programs" in programs:
            for program_id, program_data in programs["training_programs"].items():
                if name_lower in program_data.get("name", "").lower():
                    results.append({
                        "type": "program",
                        "id": program_id,
                        "data": program_data
                    })
        
        # 搜尋基礎訓練
        basic_configs = self.get_basic_training_configs()
        if "categories" in basic_configs:
            for basic_id, basic_data in basic_configs["categories"].items():
                if name_lower in basic_data.get("name", "").lower():
                    results.append({
                        "type": "basic_training",
                        "id": basic_id,
                        "data": basic_data
                    })
        
        # 搜尋課程訓練
        course_configs = self.get_course_training_configs()
        if "categories" in course_configs:
            for course_id, course_data in course_configs["categories"].items():
                if name_lower in course_data.get("name", "").lower():
                    results.append({
                        "type": "course_training",
                        "id": course_id,
                        "data": course_data
                    })
        
        # 搜尋熱身
        warmup_configs = self.get_warmup_configs()
        if "categories" in warmup_configs:
            for warmup_id, warmup_data in warmup_configs["categories"].items():
                if name_lower in warmup_data.get("name", "").lower():
                    results.append({
                        "type": "warmup",
                        "id": warmup_id,
                        "data": warmup_data
                    })
        
        # 搜尋進階訓練
        advanced_configs = self.get_advanced_configs()
        if "categories" in advanced_configs:
            for advanced_id, advanced_data in advanced_configs["categories"].items():
                if name_lower in advanced_data.get("name", "").lower():
                    results.append({
                        "type": "advanced",
                        "id": advanced_id,
                        "data": advanced_data
                    })
        
        return results


# 全域配置管理器實例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """取得全域配置管理器實例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_all_configs():
    """重新載入所有配置"""
    global _config_manager
    if _config_manager is not None:
        _config_manager.reload_config()
