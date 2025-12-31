# PeraperaServer

一个基于 FastAPI 的现代化后端服务框架。

## 项目特性

- ⚡ **FastAPI** - 高性能的现代 Python Web 框架
- 🔐 **JWT 认证** - 基于 Token 的安全认证系统
- 🗄️ **PostgreSQL** - 使用 asyncpg 的异步数据库操作
- 📝 **Pydantic** - 数据验证和设置管理
- 🔄 **异步支持** - 全异步数据库和 API 操作
- 📚 **自动文档** - Swagger UI 和 ReDoc 自动生成
- 🧪 **测试支持** - 集成 pytest 测试框架

## 项目结构

```
PeraperaServer/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # API 路由汇总
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py     # 认证端点
│   │           └── users.py    # 用户端点
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库连接
│   │   └── security.py         # 安全工具
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py             # 用户模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py             # 用户模式
│   └── services/
│       └── __init__.py
├── .env.example                # 环境变量示例
├── .gitignore
├── requirements.txt            # 项目依赖
└── README.md
```

## 快速开始

### 1. 克隆项目（如果需要）

```bash
git clone <repository-url>
cd PeraperaServer
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装 PostgreSQL

确保已安装 PostgreSQL 数据库：

**macOS (使用 Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**创建数据库:**
```bash
# 进入 PostgreSQL 命令行
psql -U postgres

# 在 psql 中执行
CREATE DATABASE perapera_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE perapera_db TO postgres;
\q
```

### 4. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 5. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，修改以下配置：
# - DATABASE_URL: 数据库连接字符串
# - SECRET_KEY: JWT 密钥（生产环境必须修改）
```

数据库连接字符串格式：
```
postgresql+asyncpg://username:password@host:port/database_name
```

**快速初始化（可选）:**

使用提供的脚本快速创建数据库：
```bash
# 方式 1: 使用 Shell 脚本（仅创建数据库）
chmod +x scripts/init_db.sh
./scripts/init_db.sh

# 方式 2: 使用 Python 脚本（创建数据表）
python3 scripts/init_db.py
```

### 6. 运行服务器

**方式 1：使用启动脚本（推荐）**
```bash
python3 run.py
```

**方式 2：使用 uvicorn**
```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**方式 3：在虚拟环境中**
```bash
# 如果已激活虚拟环境
uvicorn app.main:app --reload
```

服务器将在 `http://localhost:8000` 启动。

## API 文档

启动服务器后，可以访问以下地址查看自动生成的 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API 端点

### 基础端点

- `GET /` - 欢迎页面
- `GET /health` - 健康检查

### 认证端点

- `POST /api/v1/auth/login` - 用户登录，获取访问令牌

### 用户端点

- `POST /api/v1/users/` - 创建新用户
- `GET /api/v1/users/me` - 获取当前用户信息
- `GET /api/v1/users/{user_id}` - 获取指定用户信息
- `GET /api/v1/users/` - 获取用户列表
- `PUT /api/v1/users/{user_id}` - 更新用户信息
- `DELETE /api/v1/users/{user_id}` - 删除用户

## 使用示例

### 1. 创建用户

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "password123"
  }'
```

### 2. 用户登录

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

### 3. 获取当前用户信息

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer <your-access-token>"
```

## 开发指南

### 添加新的 API 端点

1. 在 `app/models/` 中创建数据模型
2. 在 `app/schemas/` 中创建 Pydantic 模式
3. 在 `app/api/v1/endpoints/` 中创建端点文件
4. 在 `app/api/v1/router.py` 中注册路由

### 数据库迁移

项目使用 SQLAlchemy 的自动建表功能。如需使用 Alembic 进行数据库迁移：

```bash
# 初始化 Alembic
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Initial migration"

# 应用迁移
alembic upgrade head
```

## 测试

```bash
pytest
```

## 环境变量说明

- `APP_NAME`: 应用名称
- `APP_VERSION`: 应用版本
- `DEBUG`: 调试模式
- `HOST`: 服务器主机
- `PORT`: 服务器端口
- `DATABASE_URL`: 数据库连接 URL
- `SECRET_KEY`: JWT 密钥（生产环境必须修改）
- `ALGORITHM`: JWT 算法
- `ACCESS_TOKEN_EXPIRE_MINUTES`: 访问令牌过期时间（分钟）
- `ALLOWED_ORIGINS`: CORS 允许的源

## 技术栈

- **FastAPI** - Web 框架
- **Uvicorn** - ASGI 服务器
- **PostgreSQL** - 关系型数据库
- **SQLAlchemy** - ORM
- **asyncpg** - 异步 PostgreSQL 驱动
- **Pydantic** - 数据验证
- **Python-Jose** - JWT 处理
- **Passlib** - 密码哈希
- **Pytest** - 测试框架

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
