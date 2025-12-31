#!/bin/bash

# PostgreSQL 数据库初始化脚本

echo "正在创建 PostgreSQL 数据库..."

# 数据库配置
DB_NAME="perapera_db"
DB_USER="postgres"
DB_PASSWORD="postgres"

# 检查 PostgreSQL 是否运行
if ! pg_isready -q; then
    echo "错误: PostgreSQL 服务未运行"
    echo "请先启动 PostgreSQL 服务:"
    echo "  macOS: brew services start postgresql@15"
    echo "  Linux: sudo systemctl start postgresql"
    exit 1
fi

# 创建数据库
echo "创建数据库 $DB_NAME..."
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
psql -U postgres -c "CREATE DATABASE $DB_NAME;"

# 授予权限
echo "授予权限..."
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "✅ 数据库初始化完成！"
echo ""
echo "数据库信息:"
echo "  数据库名: $DB_NAME"
echo "  用户名: $DB_USER"
echo "  连接字符串: postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "请确保 .env 文件中的 DATABASE_URL 配置正确。"
