from typing import Dict, Optional
from enum import Enum


class Language(str, Enum):
    """支持的语言"""
    EN = "en"
    ZH = "zh"
    JA = "ja"
    KO = "ko"


# 翻译字典
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # 通用消息
    "welcome_message": {
        "en": "Welcome to {app_name}",
        "zh": "欢迎使用 {app_name}",
        "ja": "{app_name}へようこそ",
        "ko": "{app_name}에 오신 것을 환영합니다"
    },
    "healthy": {
        "en": "healthy",
        "zh": "健康",
        "ja": "正常",
        "ko": "정상"
    },
    
    # 认证相关
    "invalid_email_format": {
        "en": "Invalid email format",
        "zh": "邮箱格式无效",
        "ja": "メールアドレスの形式が無効です",
        "ko": "이메일 형식이 잘못되었습니다"
    },
    "invalid_or_expired_captcha": {
        "en": "Invalid or expired captcha",
        "zh": "验证码无效或已过期",
        "ja": "認証コードが無効または期限切れです",
        "ko": "인증 코드가 유효하지 않거나 만료되었습니다"
    },
    "inactive_user": {
        "en": "Inactive user",
        "zh": "用户未激活",
        "ja": "ユーザーが無効です",
        "ko": "비활성 사용자"
    },
    "captcha_sent_successfully": {
        "en": "Captcha sent successfully",
        "zh": "验证码发送成功",
        "ja": "認証コードが正常に送信されました",
        "ko": "인증 코드가 성공적으로 전송되었습니다"
    },
    "failed_to_send_email": {
        "en": "Failed to send email",
        "zh": "邮件发送失败",
        "ja": "メール送信に失敗しました",
        "ko": "이메일 전송 실패"
    },
    "wait_before_requesting": {
        "en": "Please wait {seconds} seconds before requesting another captcha",
        "zh": "请等待 {seconds} 秒后再请求验证码",
        "ja": "次の認証コードをリクエストする前に {seconds} 秒お待ちください",
        "ko": "다음 인증 코드를 요청하기 전에 {seconds}초 기다려주세요"
    },
    "incorrect_username_or_password": {
        "en": "Incorrect username or password",
        "zh": "用户名或密码错误",
        "ja": "ユーザー名またはパスワードが正しくありません",
        "ko": "사용자 이름 또는 비밀번호가 올바르지 않습니다"
    },
    "could_not_validate_credentials": {
        "en": "Could not validate credentials",
        "zh": "无法验证凭据",
        "ja": "認証情報を検証できませんでした",
        "ko": "자격 증명을 확인할 수 없습니다"
    },
    
    # 用户相关
    "user_already_exists": {
        "en": "User with this email or username already exists",
        "zh": "该邮箱或用户名已存在",
        "ja": "このメールアドレスまたはユーザー名は既に存在します",
        "ko": "이 이메일 또는 사용자 이름이 이미 존재합니다"
    },
    "user_not_found": {
        "en": "User not found",
        "zh": "用户不存在",
        "ja": "ユーザーが見つかりません",
        "ko": "사용자를 찾을 수 없습니다"
    },
    "not_enough_permissions": {
        "en": "Not enough permissions",
        "zh": "权限不足",
        "ja": "権限が不足しています",
        "ko": "권한이 부족합니다"
    },
    
    # 邮件相关
    "email_subject_captcha": {
        "en": "Your Verification Code",
        "zh": "您的验证码",
        "ja": "認証コード",
        "ko": "인증 코드"
    },
    "email_captcha_title": {
        "en": "Verification Code",
        "zh": "验证码",
        "ja": "認証コード",
        "ko": "인증 코드"
    },
    "email_captcha_body": {
        "en": "Your verification code is: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "zh": "您的验证码是: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "ja": "認証コードは: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "ko": "인증 코드는: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>"
    },
    "email_captcha_validity": {
        "en": "The verification code is valid for 10 minutes. Please do not share it with others.",
        "zh": "验证码有效期为10分钟，请勿泄露给他人。",
        "ja": "認証コードは10分間有効です。他の人と共有しないでください。",
        "ko": "인증 코드는 10분간 유효합니다. 다른 사람과 공유하지 마세요."
    },
    "email_captcha_ignore": {
        "en": "If this was not you, please ignore this email.",
        "zh": "如果这不是您的操作，请忽略此邮件。",
        "ja": "これがあなたの操作でない場合は、このメールを無視してください。",
        "ko": "본인이 아닌 경우 이 이메일을 무시하세요."
    }
}


def get_translation(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    获取翻译文本
    
    Args:
        key: 翻译键
        lang: 语言代码 (en, zh, ja, ko)
        **kwargs: 格式化参数
    
    Returns:
        翻译后的文本
    """
    # 默认使用英文
    if not lang or lang not in [Language.EN, Language.ZH, Language.JA, Language.KO]:
        lang = Language.EN
    
    # 获取翻译
    translations = TRANSLATIONS.get(key, {})
    text = translations.get(lang, translations.get(Language.EN, key))
    
    # 格式化文本
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    
    return text


def get_language_from_header(accept_language: Optional[str] = None) -> str:
    """
    从 Accept-Language header 解析语言
    
    Args:
        accept_language: Accept-Language header 值
    
    Returns:
        语言代码
    """
    if not accept_language:
        return Language.EN
    
    # 解析语言代码（取第一个）
    lang_code = accept_language.split(',')[0].split('-')[0].lower()
    
    # 映射到支持的语言
    lang_map = {
        'en': Language.EN,
        'zh': Language.ZH,
        'ja': Language.JA,
        'ko': Language.KO,
    }
    
    return lang_map.get(lang_code, Language.EN)
