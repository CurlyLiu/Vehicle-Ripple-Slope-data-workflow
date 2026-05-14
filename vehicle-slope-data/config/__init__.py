"""
Slope Data Configuration Manager
References vehicle-ripple-data configuration system
"""

import sys
from pathlib import Path

# Add ripple-data to path to reuse ConfigManager
ripple_path = Path(__file__).parent.parent.parent / 'vehicle-ripple-data'
if str(ripple_path) not in sys.path:
    sys.path.insert(0, str(ripple_path))

# Import from ripple-data config module (avoid circular import with different name)
try:
    from config import ConfigManager, load_config, get_config_manager, reload_config
except ImportError:
    # If ripple-data config is not available, create minimal implementation
    import yaml
    
    class ConfigManager:
        """Minimal config manager for standalone use"""
        def __init__(self, skill_root, hot_reload=True):
            self.skill_root = Path(skill_root)
            self.config_dir = self.skill_root / 'config'
            self._cache = {}
        
        def load(self, config_name, use_cache=True):
            if use_cache and config_name in self._cache:
                return self._cache[config_name]
            
            config_file = self.config_dir / f"{config_name}.yaml"
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self._cache[config_name] = config
            return config
    
    def load_config(config_name):
        return ConfigManager(Path(__file__).parent.parent).load(config_name)
    
    def get_config_manager():
        return ConfigManager(Path(__file__).parent.parent)
    
    def reload_config(config_name=None):
        pass

__all__ = ['ConfigManager', 'load_config', 'get_config_manager', 'reload_config', 'get_slope_config_manager']


class SlopeConfigManager:
    """
    Slope Data专用配置管理器
    复用ripple-data的基础配置，添加slope特有配置
    """
    
    def __init__(self, hot_reload: bool = True):
        # ripple-data skill根目录
        ripple_root = Path(__file__).parent.parent.parent / 'vehicle-ripple-data'
        # slope-data skill根目录
        slope_root = Path(__file__).parent.parent
        
        self.ripple_config_mgr = ConfigManager(ripple_root, hot_reload)
        self.slope_root = slope_root
        self._slope_cache = {}
    
    def load(self, config_name: str, use_cache: bool = True):
        """
        加载配置
        
        策略：
        - common/*: 从ripple-data加载共享配置
        - slope/*: 从slope-data加载特有配置
        """
        if config_name.startswith('common/'):
            # 从ripple-data加载共享配置
            return self.ripple_config_mgr.load(config_name, use_cache)
        elif config_name.startswith('slope/'):
            # 从slope-data加载特有配置
            return self._load_slope_config(config_name, use_cache)
        else:
            # 默认尝试从slope-data加载
            return self._load_slope_config(f'slope/{config_name}', use_cache)
    
    def _load_slope_config(self, config_name: str, use_cache: bool = True):
        """加载slope特有配置"""
        import yaml
        
        cache_key = config_name
        if use_cache and cache_key in self._slope_cache:
            return self._slope_cache[cache_key]
        
        config_file = self.slope_root / 'config' / f"{config_name}.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Slope config not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self._slope_cache[cache_key] = config
        return config
    
    def reload(self, config_name: str = None):
        """重新加载配置"""
        if config_name is None:
            self.ripple_config_mgr.reload()
            self._slope_cache.clear()
        elif config_name.startswith('common/'):
            self.ripple_config_mgr.reload(config_name)
        elif config_name.startswith('slope/'):
            self._slope_cache.pop(config_name, None)
            return self.load(config_name)


def get_slope_config_manager(hot_reload: bool = True) -> SlopeConfigManager:
    """获取SlopeConfigManager单例"""
    if not hasattr(get_slope_config_manager, '_instance'):
        get_slope_config_manager._instance = SlopeConfigManager(hot_reload)
    return get_slope_config_manager._instance
