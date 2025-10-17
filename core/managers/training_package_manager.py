"""
訓練套餐管理器

這個模組負責管理訓練套餐的創建、編輯、保存和載入，包括：
- 訓練套餐配置管理
- 自定義套餐創建和編輯
- 套餐導入導出功能
- 套餐模板管理
"""

import json
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class TrainingPackage:
    """訓練套餐類別"""
    
    def __init__(self, package_id: str, name: str, description: str = "", 
                 package_type: str = "basic", created_by: str = "system"):
        """
        初始化訓練套餐
        
        Args:
            package_id: 套餐ID
            name: 套餐名稱
            description: 套餐描述
            package_type: 套餐類型 (basic, advanced, custom)
            created_by: 創建者
        """
        self.package_id = package_id
        self.name = name
        self.description = description
        self.package_type = package_type
        self.created_by = created_by
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.version = "1.0"
        
        # 套餐配置
        self.config = {
            "shots": [],  # 發球配置列表
            "sections": [],  # 發球區域列表
            "mode": "sequence",  # 發球模式
            "interval": 3.0,  # 發球間隔
            "total_shots": 0,  # 總發球數
            "unlimited": False,  # 是否無限發球
            "difficulty": "medium",  # 難度等級
            "duration": 0,  # 預估時長（秒）
            "tags": [],  # 標籤
            "machine_requirements": 1,  # 所需機器數量
        }
    
    def add_shot(self, section: str, description: str = "", 
                 speed: str = "normal", count: int = 1) -> bool:
        """
        添加發球配置
        
        Args:
            section: 發球區域
            description: 描述
            speed: 速度
            count: 數量
            
        Returns:
            是否成功添加
        """
        try:
            shot_config = {
                "section": section,
                "description": description,
                "speed": speed,
                "count": count,
                "order": len(self.config["shots"]) + 1
            }
            
            self.config["shots"].append(shot_config)
            self._update_metadata()
            return True
            
        except Exception as e:
            print(f"添加發球配置失敗: {e}")
            return False
    
    def remove_shot(self, index: int) -> bool:
        """
        移除發球配置
        
        Args:
            index: 發球配置索引
            
        Returns:
            是否成功移除
        """
        try:
            if 0 <= index < len(self.config["shots"]):
                del self.config["shots"][index]
                self._update_metadata()
                return True
            return False
            
        except Exception as e:
            print(f"移除發球配置失敗: {e}")
            return False
    
    def update_shot(self, index: int, section: str = None, description: str = None,
                   speed: str = None, count: int = None) -> bool:
        """
        更新發球配置
        
        Args:
            index: 發球配置索引
            section: 發球區域
            description: 描述
            speed: 速度
            count: 數量
            
        Returns:
            是否成功更新
        """
        try:
            if 0 <= index < len(self.config["shots"]):
                shot = self.config["shots"][index]
                
                if section is not None:
                    shot["section"] = section
                if description is not None:
                    shot["description"] = description
                if speed is not None:
                    shot["speed"] = speed
                if count is not None:
                    shot["count"] = count
                
                self._update_metadata()
                return True
            return False
            
        except Exception as e:
            print(f"更新發球配置失敗: {e}")
            return False
    
    def set_sections(self, sections: List[str]) -> bool:
        """
        設置發球區域列表
        
        Args:
            sections: 發球區域列表
            
        Returns:
            是否成功設置
        """
        try:
            self.config["sections"] = sections.copy()
            self._update_metadata()
            return True
            
        except Exception as e:
            print(f"設置發球區域失敗: {e}")
            return False
    
    def set_mode(self, mode: str) -> bool:
        """
        設置發球模式
        
        Args:
            mode: 發球模式 (sequence, random, wave)
            
        Returns:
            是否成功設置
        """
        try:
            valid_modes = ["sequence", "random", "wave", "simultaneous"]
            if mode in valid_modes:
                self.config["mode"] = mode
                self._update_metadata()
                return True
            return False
            
        except Exception as e:
            print(f"設置發球模式失敗: {e}")
            return False
    
    def set_interval(self, interval: float) -> bool:
        """
        設置發球間隔
        
        Args:
            interval: 發球間隔（秒）
            
        Returns:
            是否成功設置
        """
        try:
            if 0.1 <= interval <= 10.0:
                self.config["interval"] = interval
                self._update_metadata()
                return True
            return False
            
        except Exception as e:
            print(f"設置發球間隔失敗: {e}")
            return False
    
    def set_difficulty(self, difficulty: str) -> bool:
        """
        設置難度等級
        
        Args:
            difficulty: 難度等級 (easy, medium, hard, expert)
            
        Returns:
            是否成功設置
        """
        try:
            valid_difficulties = ["easy", "medium", "hard", "expert"]
            if difficulty in valid_difficulties:
                self.config["difficulty"] = difficulty
                self._update_metadata()
                return True
            return False
            
        except Exception as e:
            print(f"設置難度等級失敗: {e}")
            return False
    
    def add_tag(self, tag: str) -> bool:
        """
        添加標籤
        
        Args:
            tag: 標籤
            
        Returns:
            是否成功添加
        """
        try:
            if tag and tag not in self.config["tags"]:
                self.config["tags"].append(tag)
                self._update_metadata()
                return True
            return False
            
        except Exception as e:
            print(f"添加標籤失敗: {e}")
            return False
    
    def remove_tag(self, tag: str) -> bool:
        """
        移除標籤
        
        Args:
            tag: 標籤
            
        Returns:
            是否成功移除
        """
        try:
            if tag in self.config["tags"]:
                self.config["tags"].remove(tag)
                self._update_metadata()
                return True
            return False
            
        except Exception as e:
            print(f"移除標籤失敗: {e}")
            return False
    
    def _update_metadata(self):
        """更新元數據"""
        self.updated_at = datetime.now().isoformat()
        
        # 計算總發球數
        total_shots = sum(shot["count"] for shot in self.config["shots"])
        self.config["total_shots"] = total_shots
        
        # 計算預估時長
        if self.config["interval"] > 0:
            self.config["duration"] = total_shots * self.config["interval"]
        else:
            self.config["duration"] = 0
        
        # 更新所需機器數量
        if self.package_type == "coordinated":
            self.config["machine_requirements"] = 4
        else:
            self.config["machine_requirements"] = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "package_id": self.package_id,
            "name": self.name,
            "description": self.description,
            "package_type": self.package_type,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "config": self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingPackage':
        """從字典創建訓練套餐"""
        package = cls(
            package_id=data["package_id"],
            name=data["name"],
            description=data.get("description", ""),
            package_type=data.get("package_type", "basic"),
            created_by=data.get("created_by", "system")
        )
        
        package.created_at = data.get("created_at", package.created_at)
        package.updated_at = data.get("updated_at", package.updated_at)
        package.version = data.get("version", "1.0")
        package.config = data.get("config", package.config)
        
        return package
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        驗證套餐配置
        
        Returns:
            (是否有效, 錯誤列表)
        """
        errors = []
        
        # 檢查基本屬性
        if not self.package_id:
            errors.append("套餐ID不能為空")
        
        if not self.name:
            errors.append("套餐名稱不能為空")
        
        # 檢查配置
        if not self.config["shots"] and not self.config["sections"]:
            errors.append("套餐必須包含發球配置或發球區域")
        
        # 檢查發球配置
        for i, shot in enumerate(self.config["shots"]):
            if not shot.get("section"):
                errors.append(f"第{i+1}個發球配置缺少區域")
            
            if shot.get("count", 0) <= 0:
                errors.append(f"第{i+1}個發球配置數量必須大於0")
        
        # 檢查發球間隔
        if not (0.1 <= self.config["interval"] <= 10.0):
            errors.append("發球間隔必須在0.1-10.0秒之間")
        
        return len(errors) == 0, errors


class TrainingPackageManager:
    """訓練套餐管理器"""
    
    def __init__(self, packages_dir: str = "training_packages"):
        """
        初始化訓練套餐管理器
        
        Args:
            packages_dir: 套餐文件目錄
        """
        self.packages_dir = packages_dir
        self.packages: Dict[str, TrainingPackage] = {}
        self.templates: Dict[str, TrainingPackage] = {}
        
        # 確保目錄存在
        os.makedirs(packages_dir, exist_ok=True)
        os.makedirs(os.path.join(packages_dir, "templates"), exist_ok=True)
        
        # 載入套餐
        self._load_packages()
        self._load_templates()
        self._create_default_templates()
    
    def _load_packages(self):
        """載入套餐文件"""
        try:
            packages_file = os.path.join(self.packages_dir, "packages.json")
            if os.path.exists(packages_file):
                with open(packages_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for package_data in data.get("packages", []):
                    package = TrainingPackage.from_dict(package_data)
                    self.packages[package.package_id] = package
                
                print(f"載入了 {len(self.packages)} 個訓練套餐")
            
        except Exception as e:
            print(f"載入套餐文件失敗: {e}")
    
    def _load_templates(self):
        """載入模板文件"""
        try:
            templates_dir = os.path.join(self.packages_dir, "templates")
            for filename in os.listdir(templates_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(templates_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    package = TrainingPackage.from_dict(data)
                    self.templates[package.package_id] = package
            
            print(f"載入了 {len(self.templates)} 個訓練套餐模板")
            
        except Exception as e:
            print(f"載入模板文件失敗: {e}")
    
    def _create_default_templates(self):
        """創建預設模板"""
        if not self.templates:
            # 基礎訓練模板
            basic_template = TrainingPackage(
                "basic_template", "基礎訓練模板", "適合初學者的基礎訓練", "basic"
            )
            basic_template.add_shot("sec1_1", "正手發球", "normal", 5)
            basic_template.add_shot("sec2_1", "反手發球", "normal", 5)
            basic_template.add_shot("sec3_1", "網前球", "slow", 3)
            basic_template.set_interval(3.0)
            basic_template.set_difficulty("easy")
            basic_template.add_tag("基礎")
            basic_template.add_tag("初學者")
            
            # 進階訓練模板
            advanced_template = TrainingPackage(
                "advanced_template", "進階訓練模板", "適合有經驗選手的進階訓練", "advanced"
            )
            advanced_template.set_sections(["sec1_1", "sec2_1", "sec3_1", "sec4_1", "sec5_1"])
            advanced_template.set_mode("random")
            advanced_template.set_interval(2.5)
            advanced_template.set_difficulty("hard")
            advanced_template.add_tag("進階")
            advanced_template.add_tag("隨機")
            
            # 協調訓練模板
            coordinated_template = TrainingPackage(
                "coordinated_template", "協調訓練模板", "四台發球機協調訓練", "coordinated"
            )
            coordinated_template.set_sections(["sec1_1", "sec2_1", "sec3_1", "sec4_1"])
            coordinated_template.set_mode("wave")
            coordinated_template.set_interval(1.0)
            coordinated_template.set_difficulty("expert")
            coordinated_template.add_tag("協調")
            coordinated_template.add_tag("四台")
            
            # 保存模板
            self.templates["basic_template"] = basic_template
            self.templates["advanced_template"] = advanced_template
            self.templates["coordinated_template"] = coordinated_template
            
            self._save_templates()
    
    def _save_packages(self):
        """保存套餐文件"""
        try:
            packages_file = os.path.join(self.packages_dir, "packages.json")
            data = {
                "packages": [package.to_dict() for package in self.packages.values()],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(packages_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"保存了 {len(self.packages)} 個訓練套餐")
            
        except Exception as e:
            print(f"保存套餐文件失敗: {e}")
    
    def _save_templates(self):
        """保存模板文件"""
        try:
            templates_dir = os.path.join(self.packages_dir, "templates")
            for package in self.templates.values():
                filepath = os.path.join(templates_dir, f"{package.package_id}.json")
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(package.to_dict(), f, ensure_ascii=False, indent=2)
            
            print(f"保存了 {len(self.templates)} 個訓練套餐模板")
            
        except Exception as e:
            print(f"保存模板文件失敗: {e}")
    
    def create_package(self, package_id: str, name: str, description: str = "",
                      package_type: str = "basic", created_by: str = "user") -> Optional[TrainingPackage]:
        """
        創建新套餐
        
        Args:
            package_id: 套餐ID
            name: 套餐名稱
            description: 套餐描述
            package_type: 套餐類型
            created_by: 創建者
            
        Returns:
            創建的套餐，如果失敗則返回None
        """
        try:
            if package_id in self.packages:
                print(f"套餐ID {package_id} 已存在")
                return None
            
            package = TrainingPackage(package_id, name, description, package_type, created_by)
            self.packages[package_id] = package
            
            self._save_packages()
            return package
            
        except Exception as e:
            print(f"創建套餐失敗: {e}")
            return None
    
    def get_package(self, package_id: str) -> Optional[TrainingPackage]:
        """
        獲取套餐
        
        Args:
            package_id: 套餐ID
            
        Returns:
            套餐，如果不存在則返回None
        """
        return self.packages.get(package_id)
    
    def get_all_packages(self) -> Dict[str, TrainingPackage]:
        """
        獲取所有套餐
        
        Returns:
            所有套餐的字典
        """
        return self.packages.copy()
    
    def get_packages_by_type(self, package_type: str) -> Dict[str, TrainingPackage]:
        """
        根據類型獲取套餐
        
        Args:
            package_type: 套餐類型
            
        Returns:
            指定類型的套餐字典
        """
        return {
            package_id: package for package_id, package in self.packages.items()
            if package.package_type == package_type
        }
    
    def get_packages_by_tag(self, tag: str) -> Dict[str, TrainingPackage]:
        """
        根據標籤獲取套餐
        
        Args:
            tag: 標籤
            
        Returns:
            包含指定標籤的套餐字典
        """
        return {
            package_id: package for package_id, package in self.packages.items()
            if tag in package.config["tags"]
        }
    
    def update_package(self, package_id: str, **kwargs) -> bool:
        """
        更新套餐
        
        Args:
            package_id: 套餐ID
            **kwargs: 要更新的屬性
            
        Returns:
            是否成功更新
        """
        try:
            package = self.packages.get(package_id)
            if not package:
                return False
            
            # 更新屬性
            if "name" in kwargs:
                package.name = kwargs["name"]
            if "description" in kwargs:
                package.description = kwargs["description"]
            if "package_type" in kwargs:
                package.package_type = kwargs["package_type"]
            
            package.updated_at = datetime.now().isoformat()
            
            self._save_packages()
            return True
            
        except Exception as e:
            print(f"更新套餐失敗: {e}")
            return False
    
    def delete_package(self, package_id: str) -> bool:
        """
        刪除套餐
        
        Args:
            package_id: 套餐ID
            
        Returns:
            是否成功刪除
        """
        try:
            if package_id in self.packages:
                del self.packages[package_id]
                self._save_packages()
                return True
            return False
            
        except Exception as e:
            print(f"刪除套餐失敗: {e}")
            return False
    
    def duplicate_package(self, package_id: str, new_package_id: str, new_name: str) -> Optional[TrainingPackage]:
        """
        複製套餐
        
        Args:
            package_id: 原套餐ID
            new_package_id: 新套餐ID
            new_name: 新套餐名稱
            
        Returns:
            複製的套餐，如果失敗則返回None
        """
        try:
            original = self.packages.get(package_id)
            if not original:
                return None
            
            if new_package_id in self.packages:
                print(f"套餐ID {new_package_id} 已存在")
                return None
            
            # 創建副本
            package_data = original.to_dict()
            package_data["package_id"] = new_package_id
            package_data["name"] = new_name
            package_data["created_by"] = "user"
            package_data["created_at"] = datetime.now().isoformat()
            package_data["updated_at"] = package_data["created_at"]
            
            new_package = TrainingPackage.from_dict(package_data)
            self.packages[new_package_id] = new_package
            
            self._save_packages()
            return new_package
            
        except Exception as e:
            print(f"複製套餐失敗: {e}")
            return None
    
    def create_from_template(self, template_id: str, package_id: str, name: str) -> Optional[TrainingPackage]:
        """
        從模板創建套餐
        
        Args:
            template_id: 模板ID
            package_id: 新套餐ID
            name: 新套餐名稱
            
        Returns:
            創建的套餐，如果失敗則返回None
        """
        try:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            # 檢查新套餐ID是否已存在
            if package_id in self.packages:
                return None
            
            # 創建套餐副本
            package_data = template.to_dict()
            package_data["package_id"] = package_id
            package_data["name"] = name
            package_data["created_by"] = "user"
            package_data["created_at"] = datetime.now().isoformat()
            package_data["updated_at"] = package_data["created_at"]
            
            new_package = TrainingPackage.from_dict(package_data)
            self.packages[package_id] = new_package
            
            self._save_packages()
            return new_package
            
        except Exception as e:
            print(f"從模板創建套餐失敗: {e}")
            return None
    
    def export_package(self, package_id: str, filepath: str) -> bool:
        """
        導出套餐
        
        Args:
            package_id: 套餐ID
            filepath: 導出文件路徑
            
        Returns:
            是否成功導出
        """
        try:
            package = self.packages.get(package_id)
            if not package:
                return False
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(package.to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"導出套餐失敗: {e}")
            return False
    
    def import_package(self, filepath: str) -> Optional[TrainingPackage]:
        """
        導入套餐
        
        Args:
            filepath: 導入文件路徑
            
        Returns:
            導入的套餐，如果失敗則返回None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            package = TrainingPackage.from_dict(data)
            
            # 檢查套餐ID是否已存在
            if package.package_id in self.packages:
                # 生成新的ID
                base_id = package.package_id
                counter = 1
                while f"{base_id}_{counter}" in self.packages:
                    counter += 1
                package.package_id = f"{base_id}_{counter}"
            
            self.packages[package.package_id] = package
            self._save_packages()
            
            return package
            
        except Exception as e:
            print(f"導入套餐失敗: {e}")
            return None
    
    def get_templates(self) -> Dict[str, TrainingPackage]:
        """
        獲取所有模板
        
        Returns:
            所有模板的字典
        """
        return self.templates.copy()
    
    def search_packages(self, query: str) -> Dict[str, TrainingPackage]:
        """
        搜索套餐
        
        Args:
            query: 搜索查詢
            
        Returns:
            匹配的套餐字典
        """
        query = query.lower()
        results = {}
        
        for package_id, package in self.packages.items():
            # 搜索名稱和描述
            if (query in package.name.lower() or 
                query in package.description.lower() or
                query in package.package_id.lower()):
                results[package_id] = package
                continue
            
            # 搜索標籤
            for tag in package.config["tags"]:
                if query in tag.lower():
                    results[package_id] = package
                    break
        
        return results
    
    def validate_package(self, package_id: str) -> Tuple[bool, List[str]]:
        """
        驗證套餐
        
        Args:
            package_id: 套餐ID
            
        Returns:
            (是否有效, 錯誤列表)
        """
        package = self.packages.get(package_id)
        if not package:
            return False, ["套餐不存在"]
        
        return package.validate()


def create_training_package_manager(packages_dir: str = "training_packages") -> TrainingPackageManager:
    """
    建立訓練套餐管理器的工廠函數
    
    Args:
        packages_dir: 套餐文件目錄
        
    Returns:
        TrainingPackageManager 實例
    """
    return TrainingPackageManager(packages_dir)
