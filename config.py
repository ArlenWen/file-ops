"""
配置管理模块
支持从JSON文件和环境变量加载配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self._config = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                print(f"✅ 配置文件 {self.config_file} 加载成功")
            except Exception as e:
                print(f"❌ 配置文件加载失败: {e}")
                self._config = self._get_default_config()
        else:
            print(f"⚠️  配置文件 {self.config_file} 不存在，使用默认配置")
            self._config = self._get_default_config()
            self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存到 {self.config_file}")
        except Exception as e:
            print(f"❌ 配置保存失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键
        
        Args:
            key: 配置键，支持 "server.host" 格式
            default: 默认值
            
        Returns:
            配置值
        """
        # 首先检查环境变量
        env_key = key.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        if env_value is not None:
            # 尝试转换类型
            return self._convert_env_value(env_value)
        
        # 从配置文件获取
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键，支持 "server.host" 格式
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def _convert_env_value(self, value: str) -> Any:
        """转换环境变量值的类型"""
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # JSON数组或对象
        if value.startswith('[') or value.startswith('{'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # 字符串
        return value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "server": {
                "host": "10.0.51.143",
                "port": 8000,
                "debug": False
            },
            "onlyoffice": {
                "server_url": "http://10.0.51.143:8080",
                "secret": "wIUxuAv0mXxom895nEGPKG3Bw3hm",
                "api_js_url": "http://10.0.51.143:8080/web-apps/apps/api/documents/api.js",
                "jwt_enabled": True,
                "allow_private_ip": True,
                "allow_meta_ip": True,
                "use_unauthorized_storage": True
            },
            "storage": {
                "upload_directory": "uploads",
                "max_file_size": 104857600,
                "allowed_extensions": [".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt", ".txt", ".pdf"]
            },
            "security": {
                "cors_origins": ["*"],
                "cors_credentials": True,
                "cors_methods": ["*"],
                "cors_headers": ["*"]
            },
            "ui": {
                "language": "zh-CN",
                "title": "OnlyOffice Document Editor",
                "subtitle": "在线文档编辑和协作平台",
                "theme": "default"
            },
            "editor": {
                "default_user_id": "user1",
                "default_user_name": "User",
                "auto_save": True,
                "collaborative": True,
                "comments": True,
                "download": True,
                "print": True
            },
            "network": {
                "timeout": 30,
                "retry_attempts": 3,
                "connection_check_interval": 5000
            }
        }
    
    @property
    def server_host(self) -> str:
        """服务器主机地址"""
        return self.get('server.host', '10.0.51.143')
    
    @property
    def server_port(self) -> int:
        """服务器端口"""
        return self.get('server.port', 8000)
    
    @property
    def server_url(self) -> str:
        """服务器完整URL"""
        return f"http://{self.server_host}:{self.server_port}"
    
    @property
    def onlyoffice_server_url(self) -> str:
        """OnlyOffice服务器URL"""
        return self.get('onlyoffice.server_url', 'http://10.0.51.143:8080')
    
    @property
    def onlyoffice_secret(self) -> str:
        """OnlyOffice JWT密钥"""
        return self.get('onlyoffice.secret', 'wIUxuAv0mXxom895nEGPKG3Bw3hm')
    
    @property
    def onlyoffice_api_js_url(self) -> str:
        """OnlyOffice API JS文件URL"""
        return self.get('onlyoffice.api_js_url', f'{self.onlyoffice_server_url}/web-apps/apps/api/documents/api.js')
    
    @property
    def upload_directory(self) -> str:
        """文件上传目录"""
        return self.get('storage.upload_directory', 'uploads')
    
    @property
    def allowed_extensions(self) -> list:
        """允许的文件扩展名"""
        return self.get('storage.allowed_extensions', ['.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.txt', '.pdf'])


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config


def reload_config():
    """重新加载配置"""
    global config
    config.load_config()
