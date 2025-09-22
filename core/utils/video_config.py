"""
影片配置管理器

這個模組負責管理基礎訓練項目與對應影片文件的映射關係。
"""

import os
from typing import Dict, Optional


class VideoConfig:
    """影片配置管理器"""
    
    def __init__(self, base_video_dir: str = None):
        """
        初始化影片配置
        
        Args:
            base_video_dir: 影片文件基礎目錄，如果為None則使用當前工作目錄
        """
        if base_video_dir is None:
            # 使用絕對路徑，確保路徑正確
            base_video_dir = os.path.abspath(os.getcwd())
        else:
            # 確保基礎目錄也是絕對路徑
            base_video_dir = os.path.abspath(base_video_dir)
        self.base_video_dir = base_video_dir
        
        # 訓練項目與影片文件的映射
        self.video_mapping = {
            "正手高遠球": "2-1正手高遠球_v03.mp4",
            # 可以在此添加更多訓練項目的影片映射
            # "反手高遠球": "反手高遠球.mp4",
            # "正手切球": "正手切球.mp4",
            # "反手切球": "反手切球.mp4",
            # "正手殺球": "正手殺球.mp4",
            # "反手殺球": "反手殺球.mp4",
            # "正手平抽球": "正手平抽球.mp4",
            # "反手平抽球": "反手平抽球.mp4",
            # "正手小球": "正手小球.mp4",
            # "反手小球": "反手小球.mp4",
            # "正手挑球": "正手挑球.mp4",
            # "反手挑球": "反手挑球.mp4",
            # "平推球": "平推球.mp4",
            # "正手接殺球": "正手接殺球.mp4",
            # "反手接殺球": "反手接殺球.mp4",
            # "近身接殺": "近身接殺.mp4",
        }
    
    def get_video_path(self, shot_name: str) -> Optional[str]:
        """
        根據球種名稱獲取對應的影片文件路徑
        
        Args:
            shot_name: 球種名稱
            
        Returns:
            影片文件的完整絕對路徑，如果不存在則返回None
        """
        video_filename = self.video_mapping.get(shot_name)
        if not video_filename:
            return None
        
        # 使用絕對路徑
        video_path = os.path.abspath(os.path.join(self.base_video_dir, video_filename))
        
        # 檢查文件是否存在
        if os.path.exists(video_path):
            return video_path
        else:
            return None
    
    def has_video(self, shot_name: str) -> bool:
        """
        檢查指定球種是否有對應的影片
        
        Args:
            shot_name: 球種名稱
            
        Returns:
            是否有對應的影片文件
        """
        return self.get_video_path(shot_name) is not None
    
    def get_available_videos(self) -> Dict[str, str]:
        """
        獲取所有可用的影片文件
        
        Returns:
            球種名稱到影片路徑的映射字典
        """
        available_videos = {}
        for shot_name in self.video_mapping.keys():
            video_path = self.get_video_path(shot_name)
            if video_path:
                available_videos[shot_name] = video_path
        
        return available_videos
    
    def add_video_mapping(self, shot_name: str, video_filename: str) -> bool:
        """
        添加新的影片映射
        
        Args:
            shot_name: 球種名稱
            video_filename: 影片文件名
            
        Returns:
            是否添加成功
        """
        # 使用絕對路徑檢查文件是否存在
        video_path = os.path.abspath(os.path.join(self.base_video_dir, video_filename))
        if os.path.exists(video_path):
            self.video_mapping[shot_name] = video_filename
            return True
        else:
            return False
    
    def remove_video_mapping(self, shot_name: str) -> bool:
        """
        移除影片映射
        
        Args:
            shot_name: 球種名稱
            
        Returns:
            是否移除成功
        """
        if shot_name in self.video_mapping:
            del self.video_mapping[shot_name]
            return True
        return False
    
    def update_base_directory(self, new_base_dir: str) -> bool:
        """
        更新基礎目錄
        
        Args:
            new_base_dir: 新的基礎目錄
            
        Returns:
            是否更新成功
        """
        # 使用絕對路徑
        abs_base_dir = os.path.abspath(new_base_dir)
        if os.path.exists(abs_base_dir) and os.path.isdir(abs_base_dir):
            self.base_video_dir = abs_base_dir
            return True
        return False


# 全局實例
_video_config = None


def get_video_config() -> VideoConfig:
    """
    獲取全局影片配置實例
    
    Returns:
        VideoConfig實例
    """
    global _video_config
    if _video_config is None:
        _video_config = VideoConfig()
    return _video_config


def set_video_config(video_config: VideoConfig):
    """
    設置全局影片配置實例
    
    Args:
        video_config: VideoConfig實例
    """
    global _video_config
    _video_config = video_config
