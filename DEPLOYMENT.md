# 生产环境部署指南

本文档详细说明如何将 PeraperaServer 部署到生产环境。

## 部署架构

```
Internet → Nginx (80/443) → Uvicorn (8000) → FastAPI App → PostgreSQL (5432)
```

## 前置要求

- OpenCloudOS/CentOS 8+ 或其他 Linux 发行版
- Python 3.8+
- PostgreSQL 12+
- Nginx
- 至少 1GB RAM
- 至少 10GB 磁盘空间

## 快速部署

### 方法一：使用自动化脚本（推荐）

```bash
# 1. 上传代码到服务器
scp -r PeraperaServer root@your-server:/tmp/

# 2. SSH 登录服务器
ssh root@your-server

# 3. 运行部署脚本
cd /tmp/PeraperaServer
chmod +x deploy/deploy.sh
bash deploy/deploy.sh

# 4. 配置环境变量
vi /var/www/PeraperaServer/.env

# 5. 重启服务
systemctl restart perapera.service
```

### 方法二：手动部署

#### 1. 安装系统依赖

```bash
# 安装 Python 和相关工具
sudo yum install -y python3 python3-pip python3-devel gcc

# 安装 PostgreSQL
sudo yum install -y postgresql-server postgresql-devel
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 安装 Nginx
sudo yum install -y nginx
sudo systemctl enable nginx
```

#### 2. 配置 PostgreSQL

```bash
# 设置 postgres 用户密码
sudo -u postgres psql
ALTER USER postgres PASSWORD 'your_secure_password';

# 创建应用数据库和用户
CREATE DATABASE perapera_db;
CREATE USER perapera_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE perapera_db TO perapera_user;
\q

# 配置远程访问（如果需要）
sudo vi /var/lib/pgsql/data/postgresql.conf
# 修改: listen_addresses = '*'

sudo vi /var/lib/pgsql/data/pg_hba.conf
# 添加: host all all 0.0.0.0/0 md5

sudo systemctl restart postgresql
```

#### 3. 部署应用代码

```bash
# 创建部署目录
sudo mkdir -p /var/www/PeraperaServer
cd /var/www/PeraperaServer

# 上传代码（使用 git 或 scp）
# git clone your-repo-url .
# 或使用 scp 上传

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. 配置环境变量

```bash
# 创建 .env 文件
vi /var/www/PeraperaServer/.env
```

配置内容：
```env
APP_NAME=PeraperaServer
APP_VERSION=1.0.0
DEBUG=False
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=postgresql+asyncpg://perapera_user:your_secure_password@localhost:5432/perapera_db

# 安全配置（生产环境必须修改）
SECRET_KEY=your-very-secure-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS 配置
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

#### 5. 配置 Systemd 服务

```bash
# 复制服务文件
sudo cp deploy/perapera.service /etc/systemd/system/

# 修改服务文件中的路径和用户
sudo vi /etc/systemd/system/perapera.service

# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start perapera.service
sudo systemctl enable perapera.service

# 查看状态
sudo systemctl status perapera.service
```

#### 6. 配置 Nginx

```bash
# 复制 Nginx 配置
sudo cp deploy/nginx.conf /etc/nginx/conf.d/perapera.conf

# 修改配置中的域名
sudo vi /etc/nginx/conf.d/perapera.conf

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

#### 7. 配置防火墙

```bash
# 开放 HTTP/HTTPS 端口
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# 或直接开放端口
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

## SSL/HTTPS 配置（推荐）

### 使用 Let's Encrypt 免费证书

```bash
# 安装 certbot
sudo yum install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 自动续期
sudo systemctl enable certbot-renew.timer
```

## 监控和日志

### 查看应用日志

```bash
# 查看服务日志
sudo journalctl -u perapera.service -f

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/perapera_access.log
sudo tail -f /var/log/nginx/perapera_error.log
```

### 查看服务状态

```bash
# 应用状态
sudo systemctl status perapera.service

# Nginx 状态
sudo systemctl status nginx

# PostgreSQL 状态
sudo systemctl status postgresql
```

## 更新部署

```bash
# 1. 拉取最新代码
cd /var/www/PeraperaServer
git pull origin main

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 更新依赖
pip install -r requirements.txt

# 4. 重启服务
sudo systemctl restart perapera.service
```

## 性能优化

### Uvicorn Workers 配置

在 `perapera.service` 中调整 workers 数量：
```
ExecStart=/var/www/PeraperaServer/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

推荐 workers 数量：`(2 x CPU核心数) + 1`

### 数据库连接池

在 `app/core/database.py` 中配置连接池：
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
)
```

## 备份策略

### 数据库备份

```bash
# 创建备份脚本
cat > /usr/local/bin/backup-perapera-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/perapera"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
pg_dump -U perapera_user perapera_db | gzip > $BACKUP_DIR/perapera_db_$DATE.sql.gz
# 保留最近 7 天的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup-perapera-db.sh

# 添加定时任务（每天凌晨 2 点备份）
echo "0 2 * * * /usr/local/bin/backup-perapera-db.sh" | sudo crontab -
```

## 故障排查

### 应用无法启动

```bash
# 查看详细日志
sudo journalctl -u perapera.service -n 100 --no-pager

# 检查端口占用
sudo lsof -i :8000

# 手动测试启动
cd /var/www/PeraperaServer
source venv/bin/activate
python run.py
```

### 数据库连接失败

```bash
# 测试数据库连接
psql -h localhost -U perapera_user -d perapera_db

# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 查看 PostgreSQL 日志
sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log
```

### Nginx 502 错误

```bash
# 检查应用是否运行
sudo systemctl status perapera.service

# 检查端口监听
sudo netstat -tuln | grep 8000

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/perapera_error.log
```

## 安全建议

1. **修改默认密码**：确保所有密码都是强密码
2. **使用 HTTPS**：生产环境必须使用 SSL/TLS
3. **限制数据库访问**：只允许必要的 IP 访问数据库
4. **定期更新**：及时更新系统和依赖包
5. **配置防火墙**：只开放必要的端口
6. **使用环境变量**：敏感信息不要硬编码
7. **启用日志监控**：监控异常访问和错误
8. **定期备份**：确保数据安全

## 验证部署

```bash
# 1. 检查健康状态
curl http://your-server-ip/health

# 2. 访问 API 文档
curl http://your-server-ip/docs

# 3. 测试 API
curl http://your-server-ip/api/v1/auth/test
```

## 联系支持

如有问题，请查看日志或联系技术支持。
