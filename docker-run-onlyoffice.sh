#!/bin/bash
# OnlyOffice Document Server Docker 启动脚本
# 解决私有IP访问限制问题

# 读取配置文件
if [ -f "config.json" ]; then
    JWT_SECRET=$(python3 -c "import json; print(json.load(open('config.json'))['onlyoffice']['secret'])")
    ALLOW_PRIVATE_IP=$(python3 -c "import json; print(str(json.load(open('config.json'))['onlyoffice']['allow_private_ip']).lower())")
    ALLOW_META_IP=$(python3 -c "import json; print(str(json.load(open('config.json'))['onlyoffice']['allow_meta_ip']).lower())")
    USE_UNAUTHORIZED_STORAGE=$(python3 -c "import json; print(str(json.load(open('config.json'))['onlyoffice']['use_unauthorized_storage']).lower())")
    JWT_ENABLED=$(python3 -c "import json; print(str(json.load(open('config.json'))['onlyoffice']['jwt_enabled']).lower())")
else
    echo "⚠️  配置文件 config.json 不存在，使用默认配置"
    JWT_SECRET="wIUxuAv0mXxom895nEGPpHOPKG3Bw3hm"
    ALLOW_PRIVATE_IP="true"
    ALLOW_META_IP="true"
    USE_UNAUTHORIZED_STORAGE="true"
    JWT_ENABLED="true"
fi

echo "🚀 启动OnlyOffice Document Server..."

# 停止并删除现有容器（如果存在）
sudo docker stop onlyoffice-document-server 2>/dev/null || true
sudo docker rm onlyoffice-document-server 2>/dev/null || true

# 启动新的OnlyOffice容器，使用配置文件中的设置
sudo docker run -d --name onlyoffice-document-server \
  -p 8080:80 \
  -e JWT_ENABLED=$JWT_ENABLED \
  -e JWT_SECRET=$JWT_SECRET \
  -e JWT_HEADER=Authorization \
  -e JWT_IN_BODY=false \
  -e WOPI_ENABLED=false \
  -e USE_UNAUTHORIZED_STORAGE=$USE_UNAUTHORIZED_STORAGE \
  -e ALLOW_PRIVATE_IP_ADDRESS=$ALLOW_PRIVATE_IP \
  -e ALLOW_META_IP_ADDRESS=$ALLOW_META_IP \
  onlyoffice/documentserver:9.0

echo "✅ OnlyOffice Document Server 启动完成"
echo "📝 重要环境变量说明："
echo "   - ALLOW_PRIVATE_IP_ADDRESS=$ALLOW_PRIVATE_IP: 允许访问私有IP地址"
echo "   - ALLOW_META_IP_ADDRESS=$ALLOW_META_IP: 允许访问元数据IP地址"
echo "   - USE_UNAUTHORIZED_STORAGE=$USE_UNAUTHORIZED_STORAGE: 允许未授权存储访问"
echo "   - JWT_ENABLED=$JWT_ENABLED: JWT认证启用状态"
echo ""
echo "🌐 服务地址: http://localhost:8080"
echo "🔑 JWT Secret: $JWT_SECRET"
echo ""
echo "⏳ 请等待约30秒让服务完全启动..."
