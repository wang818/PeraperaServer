"""
Python 数据库初始化脚本
用于创建数据库表结构
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import init_db

# 导入所有模型，确保 create_all 能识别全部表
from app.models.user import User  # noqa: F401
from app.models.captcha import CaptchaRecord  # noqa: F401
from app.models.user_setting import UserSetting  # noqa: F401
from app.models.iap import Product, TransactionRecord, UserEntitlement  # noqa: F401


async def main():
    """初始化数据库表结构"""
    print("正在初始化数据库表...")
    try:
        await init_db()
        print("✅ 数据库表初始化完成！")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
