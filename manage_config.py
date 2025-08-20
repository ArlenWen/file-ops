#!/usr/bin/env python3
"""
配置管理工具
用于查看、修改和验证配置文件
"""

import json
import sys
import argparse
from pathlib import Path
from config import get_config, Config


def show_config():
    """显示当前配置"""
    config = get_config()
    print("📋 当前配置:")
    print("=" * 50)
    
    print(f"🖥️  服务器配置:")
    print(f"   地址: {config.server_url}")
    print(f"   主机: {config.server_host}")
    print(f"   端口: {config.server_port}")
    
    print(f"\n📄 OnlyOffice配置:")
    print(f"   服务器: {config.onlyoffice_server_url}")
    print(f"   API JS: {config.onlyoffice_api_js_url}")
    print(f"   JWT密钥: {config.onlyoffice_secret}")
    
    print(f"\n💾 存储配置:")
    print(f"   上传目录: {config.upload_directory}")
    print(f"   允许扩展名: {', '.join(config.allowed_extensions)}")
    print(f"   最大文件大小: {config.get('storage.max_file_size', 0) / 1024 / 1024:.1f} MB")
    
    print(f"\n🌐 界面配置:")
    print(f"   标题: {config.get('ui.title', 'N/A')}")
    print(f"   副标题: {config.get('ui.subtitle', 'N/A')}")
    print(f"   语言: {config.get('ui.language', 'N/A')}")


def set_config(key: str, value: str):
    """设置配置值"""
    config = get_config()
    
    # 尝试转换值的类型
    if value.lower() in ('true', 'false'):
        value = value.lower() == 'true'
    elif value.isdigit():
        value = int(value)
    elif value.replace('.', '').isdigit():
        value = float(value)
    elif value.startswith('[') and value.endswith(']'):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    
    config.set(key, value)
    config.save_config()
    print(f"✅ 配置 {key} 已设置为: {value}")


def validate_config():
    """验证配置文件"""
    print("🔍 验证配置文件...")
    
    config_file = Path("config.json")
    if not config_file.exists():
        print("❌ 配置文件 config.json 不存在")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        print("✅ 配置文件格式正确")
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件格式错误: {e}")
        return False
    
    # 验证必要的配置项
    required_keys = [
        'server.host',
        'server.port',
        'onlyoffice.server_url',
        'onlyoffice.secret',
        'storage.upload_directory'
    ]
    
    config = get_config()
    missing_keys = []
    
    for key in required_keys:
        if config.get(key) is None:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ 缺少必要配置项: {', '.join(missing_keys)}")
        return False
    
    print("✅ 所有必要配置项都存在")
    
    # 验证目录是否存在
    upload_dir = Path(config.upload_directory)
    if not upload_dir.exists():
        print(f"⚠️  上传目录 {upload_dir} 不存在，将自动创建")
        upload_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 上传目录已创建: {upload_dir}")
    else:
        print(f"✅ 上传目录存在: {upload_dir}")
    
    return True


def reset_config():
    """重置配置为默认值"""
    config_file = Path("config.json")
    if config_file.exists():
        backup_file = Path("config.json.backup")
        config_file.rename(backup_file)
        print(f"✅ 原配置文件已备份为: {backup_file}")
    
    # 创建新的配置实例，这会生成默认配置
    config = Config()
    print("✅ 配置已重置为默认值")


def main():
    parser = argparse.ArgumentParser(description="配置管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 显示配置
    subparsers.add_parser('show', help='显示当前配置')
    
    # 设置配置
    set_parser = subparsers.add_parser('set', help='设置配置值')
    set_parser.add_argument('key', help='配置键 (如: server.host)')
    set_parser.add_argument('value', help='配置值')
    
    # 验证配置
    subparsers.add_parser('validate', help='验证配置文件')
    
    # 重置配置
    subparsers.add_parser('reset', help='重置配置为默认值')
    
    args = parser.parse_args()
    
    if args.command == 'show':
        show_config()
    elif args.command == 'set':
        set_config(args.key, args.value)
    elif args.command == 'validate':
        if validate_config():
            print("\n🎉 配置验证通过!")
        else:
            print("\n❌ 配置验证失败!")
            sys.exit(1)
    elif args.command == 'reset':
        confirm = input("确定要重置配置吗? (y/N): ")
        if confirm.lower() == 'y':
            reset_config()
        else:
            print("操作已取消")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
