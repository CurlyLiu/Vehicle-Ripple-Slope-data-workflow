"""
配置管理器 - 统一管理所有配置文件
支持热更新和分层配置
"""

import yaml
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfigMetadata:
    """配置元数据"""
    loaded_at: float
    file_path: Path
    version: str


class ConfigManager:
    """
    分层配置管理器
    
    支持：
    - 分层配置：common -> skill-specific
    - 热更新：自动检测文件变化
    - 缓存：避免重复加载
    """
    
    def __init__(self, skill_root: Path, hot_reload: bool = True):
        """
        初始化配置管理器
        
        Args:
            skill_root: Skill根目录（包含config/文件夹）
            hot_reload: 是否启用热更新
        """
        self.skill_root = Path(skill_root)
        self.config_dir = self.skill_root / 'config'
        self.hot_reload = hot_reload
        self._cache: Dict[str, Any] = {}
        self._metadata: Dict[str, ConfigMetadata] = {}
        self._check_interval = 5.0  # 热更新检查间隔（秒）
        self._last_check = 0
        
        # 确保配置目录存在
        if not self.config_dir.exists():
            raise FileNotFoundError(f"配置目录不存在: {self.config_dir}")
    
    def load(self, config_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载配置
        
        Args:
            config_name: 配置名称，如 "common/vehicle_fields" 或 "ripple/excel_template"
            use_cache: 是否使用缓存
            
        Returns:
            配置字典
        """
        # 检查热更新
        if self.hot_reload:
            self._check_hot_reload()
        
        cache_key = config_name
        
        # 检查缓存
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # 构建配置文件路径
        config_file = self.config_dir / f"{config_name}.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        # 加载YAML
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 处理继承（extends）
        if config and 'extends' in config:
            parent_config = self._load_parent(config['extends'], config_file.parent)
            config = self._merge_configs(parent_config, config)
            del config['extends']
        
        # 更新缓存
        self._cache[cache_key] = config
        self._metadata[cache_key] = ConfigMetadata(
            loaded_at=time.time(),
            file_path=config_file,
            version=config.get('version', '1.0') if config else '1.0'
        )
        
        logger.info(f"加载配置: {config_name} (v{self._metadata[cache_key].version})")
        
        return config
    
    def _load_parent(self, extends_path: str, current_dir: Path) -> Dict[str, Any]:
        """加载父配置"""
        # 处理相对路径
        if extends_path.startswith('../') or extends_path.startswith('./'):
            parent_file = current_dir / extends_path
            parent_file = parent_file.with_suffix('.yaml')
        else:
            parent_file = self.config_dir / f"{extends_path}.yaml"
        
        if not parent_file.exists():
            raise FileNotFoundError(f"父配置文件不存在: {parent_file}")
        
        with open(parent_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _merge_configs(self, parent: Dict, child: Dict) -> Dict:
        """深度合并配置"""
        merged = parent.copy()
        
        for key, value in child.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _check_hot_reload(self):
        """检查配置文件是否变化（热更新）"""
        current_time = time.time()
        
        # 限制检查频率
        if current_time - self._last_check < self._check_interval:
            return
        
        self._last_check = current_time
        
        for cache_key, metadata in list(self._metadata.items()):
            try:
                mtime = metadata.file_path.stat().st_mtime
                
                if mtime > metadata.loaded_at:
                    logger.info(f"配置已更新，重新加载: {cache_key}")
                    self.reload(cache_key)
                    
            except FileNotFoundError:
                logger.warning(f"配置文件被删除: {metadata.file_path}")
    
    def reload(self, config_name: str = None):
        """
        重新加载配置
        
        Args:
            config_name: 指定配置名称，None表示全部重新加载
        """
        if config_name:
            if config_name in self._cache:
                del self._cache[config_name]
                del self._metadata[config_name]
            return self.load(config_name)
        else:
            # 重新加载所有
            keys = list(self._cache.keys())
            self._cache.clear()
            self._metadata.clear()
            
            results = {}
            for key in keys:
                results[key] = self.load(key)
            return results
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取所有配置信息"""
        return {
            key: {
                'version': meta.version,
                'loaded_at': meta.loaded_at,
                'file_path': str(meta.file_path)
            }
            for key, meta in self._metadata.items()
        }
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        self._metadata.clear()


# 便捷函数：快速获取配置管理器实例
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager(skill_root: Path = None, hot_reload: bool = True) -> ConfigManager:
    """
    获取配置管理器单例
    
    Args:
        skill_root: Skill根目录，如果为None则自动检测
        hot_reload: 是否启用热更新
        
    Returns:
        ConfigManager实例
    """
    global _config_manager_instance
    
    if _config_manager_instance is None:
        if skill_root is None:
            # 自动检测skill根目录
            current_file = Path(__file__).resolve()
            skill_root = current_file.parent.parent
        
        _config_manager_instance = ConfigManager(skill_root, hot_reload)
    
    return _config_manager_instance


def load_config(config_name: str, skill_root: Path = None) -> Dict[str, Any]:
    """
    便捷函数：快速加载配置
    
    Args:
        config_name: 配置名称
        skill_root: Skill根目录
        
    Returns:
        配置字典
    """
    manager = get_config_manager(skill_root)
    return manager.load(config_name)


def reload_config(config_name: str = None, skill_root: Path = None):
    """
    便捷函数：重新加载配置
    
    Args:
        config_name: 配置名称，None表示全部
        skill_root: Skill根目录
    """
    manager = get_config_manager(skill_root)
    return manager.reload(config_name)
