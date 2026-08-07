from typing import Dict, Optional
from enum import Enum


class Language(str, Enum):
    """支持的语言"""
    EN = "en"
    AR = "ar"
    DE = "de"
    ES = "es"
    FIL = "fil"
    FR = "fr"
    ID = "id"
    JA = "ja"
    KO = "ko"
    MS = "ms"
    MY = "my"
    PL = "pl"
    PT = "pt"
    RU = "ru"
    TH = "th"
    TR = "tr"
    VI = "vi"
    ZH_CN = "zh-CN"
    ZH_HANT = "zh-Hant"


# 翻译字典
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # 通用消息
    "welcome_message": {
        "en": "Welcome to {app_name}",
        "ar": "مرحبا بك في {app_name}",
        "de": "Willkommen bei {app_name}",
        "es": "Bienvenido a {app_name}",
        "fil": "Maligayang pagdating sa {app_name}",
        "fr": "Bienvenue sur {app_name}",
        "id": "Selamat datang di {app_name}",
        "ja": "{app_name}へようこそ",
        "ko": "{app_name}에 오신 것을 환영합니다",
        "ms": "Selamat datang ke {app_name}",
        "my": "{app_name} မှ ကြိုဆိုပါတယ်",
        "pl": "Witamy w {app_name}",
        "pt": "Bem-vindo ao {app_name}",
        "ru": "Добро пожаловать в {app_name}",
        "th": "ยินดีต้อนรับสู่ {app_name}",
        "tr": "{app_name}'e hoş geldiniz",
        "vi": "Chào mừng đến với {app_name}",
        "zh-CN": "欢迎使用 {app_name}",
        "zh-Hant": "歡迎使用 {app_name}"
    },
    "healthy": {
        "en": "healthy",
        "ar": "سليم",
        "de": "gesund",
        "es": "saludable",
        "fil": "malusog",
        "fr": "sain",
        "id": "sehat",
        "ja": "正常",
        "ko": "정상",
        "ms": "sihat",
        "my": "ကျန်းမာ",
        "pl": "zdrowy",
        "pt": "saudável",
        "ru": "здоров",
        "th": "แข็งแรง",
        "tr": "sağlıklı",
        "vi": "khỏe mạnh",
        "zh-CN": "健康",
        "zh-Hant": "健康"
    },
    
    # 认证相关
    "invalid_email_format": {
        "en": "Invalid email format",
        "ar": "تنسيق البريد الإلكتروني غير صالح",
        "de": "Ungültiges E-Mail-Format",
        "es": "Formato de correo electrónico no válido",
        "fil": "Hindi wastong format ng email",
        "fr": "Format d'e-mail invalide",
        "id": "Format email tidak valid",
        "ja": "メールアドレスの形式が無効です",
        "ko": "이메일 형식이 잘못되었습니다",
        "ms": "Format e-mel tidak sah",
        "my": "အီးမေးလ်ပုံစံ မမှန်ကန်ပါ",
        "pl": "Nieprawidłowy format e-mail",
        "pt": "Formato de e-mail inválido",
        "ru": "Неверный формат электронной почты",
        "th": "รูปแบบอีเมลไม่ถูกต้อง",
        "tr": "Geçersiz e-posta formatı",
        "vi": "Định dạng email không hợp lệ",
        "zh-CN": "邮箱格式无效",
        "zh-Hant": "郵箱格式無效"
    },
    "invalid_or_expired_captcha": {
        "en": "Invalid or expired captcha",
        "ar": "رمز التحقق غير صالح أو منتهي الصلاحية",
        "de": "Ungültiger oder abgelaufener Captcha",
        "es": "Captcha no válido o caducado",
        "fil": "Hindi wasto o nag-expire na ang captcha",
        "fr": "Captcha invalide ou expiré",
        "id": "Captcha tidak valid atau kedaluwarsa",
        "ja": "認証コードが無効または期限切れです",
        "ko": "인증 코드가 유효하지 않거나 만료되었습니다",
        "ms": "Captcha tidak sah atau tamat tempoh",
        "my": "အတည်ပြုကုဒ် မမှန်ကန်ပါ သို့မဟုတ် သက်တမ်းကုန်ဆုံးပါပြီ",
        "pl": "Nieprawidłowy lub wygasły kod captcha",
        "pt": "Captcha inválido ou expirado",
        "ru": "Неверный или истекший код подтверждения",
        "th": "รหัสยืนยันไม่ถูกต้องหรือหมดอายุ",
        "tr": "Geçersiz veya süresi dolmuş captcha",
        "vi": "Mã xác nhận không hợp lệ hoặc đã hết hạn",
        "zh-CN": "验证码无效或已过期",
        "zh-Hant": "驗證碼無效或已過期"
    },
    "invalid_or_expired_refresh_token": {
        "en": "Invalid or expired refresh token",
        "ar": "رمز التحديث غير صالح أو منتهي الصلاحية",
        "de": "Ungültiger oder abgelaufener Refresh-Token",
        "es": "Token de actualización no válido o caducado",
        "fil": "Hindi wasto o nag-expire na ang refresh token",
        "fr": "Jeton d'actualisation invalide ou expiré",
        "id": "Token penyegaran tidak valid atau kedaluwarsa",
        "ja": "リフレッシュトークンが無効または期限切れです",
        "ko": "리프레시 토큰이 유효하지 않거나 만료되었습니다",
        "ms": "Token segar semula tidak sah atau tamat tempoh",
        "my": "ရီဖရက်ရှ် တိုကင် မမှန်ကန်ပါ သို့မဟုတ် သက်တမ်းကုန်ဆုံးပါပြီ",
        "pl": "Nieprawidłowy lub wygasły token odświeżania",
        "pt": "Token de atualização inválido ou expirado",
        "ru": "Неверный или истекший токен обновления",
        "th": "รีเฟรชโทเค็นไม่ถูกต้องหรือหมดอายุ",
        "tr": "Geçersiz veya süresi dolmuş yenileme tokeni",
        "vi": "Token làm mới không hợp lệ hoặc đã hết hạn",
        "zh-CN": "刷新令牌无效或已过期",
        "zh-Hant": "刷新令牌無效或已過期"
    },
    "inactive_user": {
        "en": "Inactive user",
        "ar": "مستخدم غير نشط",
        "de": "Inaktiver Benutzer",
        "es": "Usuario inactivo",
        "fil": "Hindi aktibong user",
        "fr": "Utilisateur inactif",
        "id": "Pengguna tidak aktif",
        "ja": "ユーザーが無効です",
        "ko": "비활성 사용자",
        "ms": "Pengguna tidak aktif",
        "my": "အသုံးပြုသူ မသက်ဝင်ပါ",
        "pl": "Nieaktywny użytkownik",
        "pt": "Usuário inativo",
        "ru": "Неактивный пользователь",
        "th": "ผู้ใช้ไม่ได้ใช้งาน",
        "tr": "Etkin olmayan kullanıcı",
        "vi": "Người dùng không hoạt động",
        "zh-CN": "用户未激活",
        "zh-Hant": "用戶未激活"
    },
    "captcha_sent_successfully": {
        "en": "Captcha sent successfully",
        "ar": "تم إرسال رمز التحقق بنجاح",
        "de": "Captcha erfolgreich gesendet",
        "es": "Captcha enviado con éxito",
        "fil": "Matagumpay na naipadala ang captcha",
        "fr": "Captcha envoyé avec succès",
        "id": "Captcha berhasil dikirim",
        "ja": "認証コードが正常に送信されました",
        "ko": "인증 코드가 성공적으로 전송되었습니다",
        "ms": "Captcha berjaya dihantar",
        "my": "အတည်ပြုကုဒ် အောင်မြင်စွာ ပေးပို့ပြီးပါပြီ",
        "pl": "Kod captcha został wysłany pomyślnie",
        "pt": "Captcha enviado com sucesso",
        "ru": "Код подтверждения успешно отправлен",
        "th": "ส่งรหัสยืนยันสำเร็จ",
        "tr": "Captcha başarıyla gönderildi",
        "vi": "Gửi mã xác nhận thành công",
        "zh-CN": "验证码发送成功",
        "zh-Hant": "驗證碼發送成功"
    },
    "account_deleted": {
        "en": "Account deleted successfully",
        "ar": "تم حذف الحساب بنجاح",
        "de": "Konto erfolgreich gelöscht",
        "es": "Cuenta eliminada con éxito",
        "fil": "Matagumpay na nabura ang account",
        "fr": "Compte supprimé avec succès",
        "id": "Akun berhasil dihapus",
        "ja": "アカウントを削除しました",
        "ko": "계정이 성공적으로 삭제되었습니다",
        "ms": "Akaun berjaya dipadamkan",
        "my": "အကောင့်ကို အောင်မြင်စွာ ဖျက်ပြီးပါပြီ",
        "pl": "Konto zostało pomyślnie usunięte",
        "pt": "Conta excluída com sucesso",
        "ru": "Аккаунт успешно удалён",
        "th": "ลบบัญชีเรียบร้อยแล้ว",
        "tr": "Hesap başarıyla silindi",
        "vi": "Đã xóa tài khoản thành công",
        "zh-CN": "账号已成功注销",
        "zh-Hant": "帳號已成功註銷"
    },
    "account_delete_failed": {
        "en": "Failed to delete account, please try again later",
        "ar": "فشل حذف الحساب، يرجى المحاولة لاحقاً",
        "de": "Konto konnte nicht gelöscht werden, bitte später erneut versuchen",
        "es": "No se pudo eliminar la cuenta, inténtelo más tarde",
        "fil": "Hindi matagumpay ang pagbura ng account, subukan mamaya",
        "fr": "Échec de la suppression du compte, veuillez réessayer plus tard",
        "id": "Gagal menghapus akun, silakan coba lagi nanti",
        "ja": "アカウントの削除に失敗しました。後でもう一度お試しください",
        "ko": "계정 삭제에 실패했습니다. 나중에 다시 시도해 주세요",
        "ms": "Gagal memadam akaun, sila cuba lagi kemudian",
        "my": "အကောင့်ဖျက်ခြင်း မအောင်မြင်ပါ၊ နောက်မှ ထပ်ကြိုးစားပါ",
        "pl": "Nie udało się usunąć konta, spróbuj ponownie później",
        "pt": "Falha ao excluir conta, tente novamente mais tarde",
        "ru": "Не удалось удалить аккаунт, попробуйте позже",
        "th": "ลบบัญชีไม่สำเร็จ กรุณาลองใหม่ภายหลัง",
        "tr": "Hesap silinemedi, lütfen daha sonra tekrar deneyin",
        "vi": "Xóa tài khoản thất bại, vui lòng thử lại sau",
        "zh-CN": "账号注销失败，请稍后重试",
        "zh-Hant": "帳號註銷失敗，請稍後重試"
    },
    "failed_to_send_email": {
        "en": "Failed to send email",
        "ar": "فشل إرسال البريد الإلكتروني",
        "de": "E-Mail konnte nicht gesendet werden",
        "es": "Error al enviar el correo electrónico",
        "fil": "Nabigo ang pagpapadala ng email",
        "fr": "Échec de l'envoi de l'e-mail",
        "id": "Gagal mengirim email",
        "ja": "メール送信に失敗しました",
        "ko": "이메일 전송 실패",
        "ms": "Gagal menghantar e-mel",
        "my": "အီးမေးလ် ပေးပို့ခြင်း မအောင်မြင်ပါ",
        "pl": "Nie udało się wysłać e-maila",
        "pt": "Falha ao enviar e-mail",
        "ru": "Не удалось отправить письмо",
        "th": "ส่งอีเมลไม่สำเร็จ",
        "tr": "E-posta gönderilemedi",
        "vi": "Gửi email thất bại",
        "zh-CN": "邮件发送失败",
        "zh-Hant": "郵件發送失敗"
    },
    "wait_before_requesting": {
        "en": "Please wait {seconds} seconds before requesting another captcha",
        "ar": "يرجى الانتظار {seconds} ثانية قبل طلب رمز تحقق آخر",
        "de": "Bitte warten Sie {seconds} Sekunden, bevor Sie einen weiteren Captcha anfordern",
        "es": "Espere {seconds} segundos antes de solicitar otro captcha",
        "fil": "Maghintay ng {seconds} segundo bago humiling ng isa pang captcha",
        "fr": "Veuillez attendre {seconds} secondes avant de demander un autre captcha",
        "id": "Harap tunggu {seconds} detik sebelum meminta captcha lain",
        "ja": "次の認証コードをリクエストする前に {seconds} 秒お待ちください",
        "ko": "다음 인증 코드를 요청하기 전에 {seconds}초 기다려주세요",
        "ms": "Sila tunggu {seconds} saat sebelum meminta captcha lain",
        "my": "အခြား captcha တောင်းခံခြင်းမပြုမီ {seconds} စက္ကန့် စောင့်ပါ",
        "pl": "Poczekaj {seconds} sekund przed wysłaniem kolejnego żądania captcha",
        "pt": "Aguarde {seconds} segundos antes de solicitar outro captcha",
        "ru": "Подождите {seconds} секунд перед запросом нового кода",
        "th": "กรุณารอ {seconds} วินาทีก่อนขอรหัสยืนยันอีกครั้ง",
        "tr": "Başka bir captcha istemeden önce {seconds} saniye bekleyin",
        "vi": "Vui lòng đợi {seconds} giây trước khi yêu cầu mã xác nhận khác",
        "zh-CN": "请等待 {seconds} 秒后再请求验证码",
        "zh-Hant": "請等待 {seconds} 秒後再請求驗證碼"
    },
    "incorrect_username_or_password": {
        "en": "Incorrect username or password",
        "ar": "اسم المستخدم أو كلمة المرور غير صحيحة",
        "de": "Falscher Benutzername oder Passwort",
        "es": "Nombre de usuario o contraseña incorrectos",
        "fil": "Maling username o password",
        "fr": "Nom d'utilisateur ou mot de passe incorrect",
        "id": "Nama pengguna atau kata sandi salah",
        "ja": "ユーザー名またはパスワードが正しくありません",
        "ko": "사용자 이름 또는 비밀번호가 올바르지 않습니다",
        "ms": "Nama pengguna atau kata laluan salah",
        "my": "အသုံးပြုသူအမည် သို့မဟုတ် စကားဝှက် မှားနေပါသည်",
        "pl": "Nieprawidłowa nazwa użytkownika lub hasło",
        "pt": "Nome de usuário ou senha incorretos",
        "ru": "Неверное имя пользователя или пароль",
        "th": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
        "tr": "Yanlış kullanıcı adı veya şifre",
        "vi": "Tên người dùng hoặc mật khẩu không đúng",
        "zh-CN": "用户名或密码错误",
        "zh-Hant": "用戶名或密碼錯誤"
    },
    "could_not_validate_credentials": {
        "en": "Could not validate credentials",
        "ar": "تعذر التحقق من بيانات الاعتماد",
        "de": "Anmeldeinformationen konnten nicht validiert werden",
        "es": "No se pudieron validar las credenciales",
        "fil": "Hindi mapatunayan ang mga kredensyal",
        "fr": "Impossible de valider les informations d'identification",
        "id": "Tidak dapat memvalidasi kredensial",
        "ja": "認証情報を検証できませんでした",
        "ko": "자격 증명을 확인할 수 없습니다",
        "ms": "Tidak dapat mengesahkan kelayakan",
        "my": "အထောက်အထားများကို အတည်မပြုနိုင်ပါ",
        "pl": "Nie można zweryfikować poświadczeń",
        "pt": "Não foi possível validar as credenciais",
        "ru": "Не удалось проверить учетные данные",
        "th": "ไม่สามารถตรวจสอบข้อมูลรับรองได้",
        "tr": "Kimlik bilgileri doğrulanamadı",
        "vi": "Không thể xác thực thông tin đăng nhập",
        "zh-CN": "无法验证凭据",
        "zh-Hant": "無法驗證憑據"
    },
    
    # 用户相关
    "user_already_exists": {
        "en": "User with this email or username already exists",
        "ar": "المستخدم بهذا البريد الإلكتروني أو اسم المستخدم موجود بالفعل",
        "de": "Benutzer mit dieser E-Mail oder diesem Benutzernamen existiert bereits",
        "es": "Ya existe un usuario con este correo electrónico o nombre de usuario",
        "fil": "Mayroon nang user sa email o username na ito",
        "fr": "Un utilisateur avec cet e-mail ou ce nom d'utilisateur existe déjà",
        "id": "Pengguna dengan email atau nama pengguna ini sudah ada",
        "ja": "このメールアドレスまたはユーザー名は既に存在します",
        "ko": "이 이메일 또는 사용자 이름이 이미 존재합니다",
        "ms": "Pengguna dengan e-mel atau nama pengguna ini sudah wujud",
        "my": "ဤအီးမေးလ် သို့မဟုတ် အသုံးပြုသူအမည်ဖြင့် အသုံးပြုသူ ရှိပြီးသားဖြစ်သည်",
        "pl": "Użytkownik z tym adresem e-mail lub nazwą użytkownika już istnieje",
        "pt": "Usuário com este e-mail ou nome de usuário já existe",
        "ru": "Пользователь с таким адресом электронной почты или именем уже существует",
        "th": "มีผู้ใช้ที่มีอีเมลหรือชื่อผู้ใช้นี้อยู่แล้ว",
        "tr": "Bu e-posta veya kullanıcı adına sahip bir kullanıcı zaten mevcut",
        "vi": "Người dùng với email hoặc tên người dùng này đã tồn tại",
        "zh-CN": "该邮箱或用户名已存在",
        "zh-Hant": "該郵箱或用戶名已存在"
    },
    "user_not_found": {
        "en": "User not found",
        "ar": "المستخدم غير موجود",
        "de": "Benutzer nicht gefunden",
        "es": "Usuario no encontrado",
        "fil": "Hindi nahanap ang user",
        "fr": "Utilisateur introuvable",
        "id": "Pengguna tidak ditemukan",
        "ja": "ユーザーが見つかりません",
        "ko": "사용자를 찾을 수 없습니다",
        "ms": "Pengguna tidak dijumpai",
        "my": "အသုံးပြုသူ မတွေ့ပါ",
        "pl": "Nie znaleziono użytkownika",
        "pt": "Usuário não encontrado",
        "ru": "Пользователь не найден",
        "th": "ไม่พบผู้ใช้",
        "tr": "Kullanıcı bulunamadı",
        "vi": "Không tìm thấy người dùng",
        "zh-CN": "用户不存在",
        "zh-Hant": "用戶不存在"
    },
    "not_enough_permissions": {
        "en": "Not enough permissions",
        "ar": "الصلاحيات غير كافية",
        "de": "Nicht genügend Berechtigungen",
        "es": "Permisos insuficientes",
        "fil": "Kulang ang mga pahintulot",
        "fr": "Permissions insuffisantes",
        "id": "Izin tidak cukup",
        "ja": "権限が不足しています",
        "ko": "권한이 부족합니다",
        "ms": "Kebenaran tidak mencukupi",
        "my": "ခွင့်ပြုချက်များ မလုံလောက်ပါ",
        "pl": "Niewystarczające uprawnienia",
        "pt": "Permissões insuficientes",
        "ru": "Недостаточно прав",
        "th": "สิทธิ์ไม่เพียงพอ",
        "tr": "Yetersiz izinler",
        "vi": "Không đủ quyền",
        "zh-CN": "权限不足",
        "zh-Hant": "權限不足"
    },
    
    # 邮件相关
    "email_subject_captcha": {
        "en": "Your Verification Code",
        "ar": "رمز التحقق الخاص بك",
        "de": "Ihr Bestätigungscode",
        "es": "Su código de verificación",
        "fil": "Ang Iyong Code ng Pagpapatunay",
        "fr": "Votre code de vérification",
        "id": "Kode Verifikasi Anda",
        "ja": "認証コード",
        "ko": "인증 코드",
        "ms": "Kod Pengesahan Anda",
        "my": "သင်၏ အတည်ပြုကုဒ်",
        "pl": "Twój kod weryfikacyjny",
        "pt": "Seu código de verificação",
        "ru": "Ваш код подтверждения",
        "th": "รหัสยืนยันของคุณ",
        "tr": "Doğrulama Kodunuz",
        "vi": "Mã xác nhận của bạn",
        "zh-CN": "您的验证码",
        "zh-Hant": "您的驗證碼"
    },
    "email_captcha_title": {
        "en": "Verification Code",
        "ar": "رمز التحقق",
        "de": "Bestätigungscode",
        "es": "Código de verificación",
        "fil": "Code ng Pagpapatunay",
        "fr": "Code de vérification",
        "id": "Kode Verifikasi",
        "ja": "認証コード",
        "ko": "인증 코드",
        "ms": "Kod Pengesahan",
        "my": "အတည်ပြုကုဒ်",
        "pl": "Kod weryfikacyjny",
        "pt": "Código de verificação",
        "ru": "Код подтверждения",
        "th": "รหัสยืนยัน",
        "tr": "Doğrulama Kodu",
        "vi": "Mã xác nhận",
        "zh-CN": "验证码",
        "zh-Hant": "驗證碼"
    },
    "email_captcha_body": {
        "en": "Your verification code is: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "ar": "رمز التحقق الخاص بك هو: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "de": "Ihr Bestätigungscode lautet: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "es": "Su código de verificación es: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "fil": "Ang iyong code ng pagpapatunay ay: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "fr": "Votre code de vérification est: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "id": "Kode verifikasi Anda adalah: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "ja": "認証コードは: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "ko": "인증 코드는: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "ms": "Kod pengesahan anda ialah: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "my": "သင်၏ အတည်ပြုကုဒ်မှာ: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "pl": "Twój kod weryfikacyjny to: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "pt": "Seu código de verificação é: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "ru": "Ваш код подтверждения: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "th": "รหัสยืนยันของคุณคือ: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "tr": "Doğrulama kodunuz: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "vi": "Mã xác nhận của bạn là: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "zh-CN": "您的验证码是: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>",
        "zh-Hant": "您的驗證碼是: <strong style=\"font-size: 24px; color: #007bff;\">{captcha}</strong>"
    },
    "email_captcha_validity": {
        "en": "The verification code is valid for 10 minutes. Please do not share it with others.",
        "ar": "رمز التحقق صالح لمدة 10 دقائق. يرجى عدم مشاركته مع الآخرين.",
        "de": "Der Bestätigungscode ist 10 Minuten gültig. Bitte teilen Sie ihn nicht mit anderen.",
        "es": "El código de verificación es válido durante 10 minutos. Por favor, no lo comparta con otros.",
        "fil": "Ang code ng pagpapatunay ay wasto sa loob ng 10 minuto. Huwag itong ibahagi sa iba.",
        "fr": "Le code de vérification est valable pendant 10 minutes. Veuillez ne pas le partager avec d'autres.",
        "id": "Kode verifikasi berlaku selama 10 menit. Jangan bagikan kepada orang lain.",
        "ja": "認証コードは10分間有効です。他の人と共有しないでください。",
        "ko": "인증 코드는 10분간 유효합니다. 다른 사람과 공유하지 마세요.",
        "ms": "Kod pengesahan sah selama 10 minit. Jangan kongsikan dengan orang lain.",
        "my": "အတည်ပြုကုဒ်သည် ၁၀ မိနစ်အတွင်း အသုံးပြုနိုင်ပါသည်။ အခြားသူများနှင့် မျှဝေခြင်း မပြုပါနှင့်။",
        "pl": "Kod weryfikacyjny jest ważny przez 10 minut. Nie udostępniaj go innym.",
        "pt": "O código de verificação é válido por 10 minutos. Por favor, não o compartilhe com outras pessoas.",
        "ru": "Код подтверждения действителен в течение 10 минут. Пожалуйста, не делитесь им с другими.",
        "th": "รหัสยืนยันมีอายุ 10 นาที กรุณาอย่าแชร์ให้ผู้อื่น",
        "tr": "Doğrulama kodu 10 dakika geçerlidir. Lütfen başkalarıyla paylaşmayın.",
        "vi": "Mã xác nhận có hiệu lực trong 10 phút. Vui lòng không chia sẻ với người khác.",
        "zh-CN": "验证码有效期为10分钟，请勿泄露给他人。",
        "zh-Hant": "驗證碼有效期為10分鐘，請勿洩露給他人。"
    },
    "email_captcha_ignore": {
        "en": "If this was not you, please ignore this email.",
        "ar": "إذا لم تكن أنت، يرجى تجاهل هذا البريد الإلكتروني.",
        "de": "Wenn Sie das nicht waren, ignorieren Sie bitte diese E-Mail.",
        "es": "Si no fue usted, por favor ignore este correo electrónico.",
        "fil": "Kung hindi ito ikaw, mangyaring huwag pansinin ang email na ito.",
        "fr": "Si ce n'était pas vous, veuillez ignorer cet e-mail.",
        "id": "Jika ini bukan Anda, harap abaikan email ini.",
        "ja": "これがあなたの操作でない場合は、このメールを無視してください。",
        "ko": "본인이 아닌 경우 이 이메일을 무시하세요.",
        "ms": "Jika ini bukan anda, sila abaikan e-mel ini.",
        "my": "ဤသည် သင်မဟုတ်ပါက ဤအီးမေးလ်ကို လျစ်လျူရှုပါ။",
        "pl": "Jeśli to nie ty, zignoruj tę wiadomość e-mail.",
        "pt": "Se não foi você, por favor ignore este e-mail.",
        "ru": "Если это были не вы, пожалуйста, проигнорируйте это письмо.",
        "th": "หากไม่ใช่คุณ กรุณาเพิกเฉยต่ออีเมลนี้",
        "tr": "Bu siz değilseniz, lütfen bu e-postayı göz ardı edin.",
        "vi": "Nếu không phải bạn, vui lòng bỏ qua email này.",
        "zh-CN": "如果这不是您的操作，请忽略此邮件。",
        "zh-Hant": "如果這不是您的操作，請忽略此郵件。"
    },

    # 字幕识别时长 / 订阅配额相关
    "quota_insufficient": {
        "en": "Insufficient subtitle recognition time: need {needed} min, only {total} min available",
        "ja": "字幕認識時間が不足しています：必要 {needed} 分、残り {total} 分",
        "ko": "자막 인식 시간이 부족합니다: 필요 {needed}분, 보유 {total}분",
        "zh-CN": "字幕识别时长不足：需要 {needed} 分钟，当前剩余 {total} 分钟",
        "zh-Hant": "字幕辨識時長不足：需要 {needed} 分鐘，目前剩餘 {total} 分鐘"
    },
    "video_duration_unavailable": {
        "en": "Could not retrieve the video duration, please try again later",
        "ja": "動画の長さを取得できませんでした。後でもう一度お試しください",
        "ko": "동영상 길이를 가져올 수 없습니다. 나중에 다시 시도해 주세요",
        "zh-CN": "无法获取视频时长信息，请稍后重试",
        "zh-Hant": "無法取得影片時長資訊，請稍後重試"
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
    supported_langs = [e.value for e in Language]
    if not lang or lang not in supported_langs:
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
    
    # 解析语言代码（取第一个，保留完整的语言-地区代码）
    lang_code = accept_language.split(',')[0].strip().lower()
    
    # 映射到支持的语言
    lang_map = {
        'en': Language.EN,
        'ar': Language.AR,
        'de': Language.DE,
        'es': Language.ES,
        'fil': Language.FIL,
        'fr': Language.FR,
        'id': Language.ID,
        'ja': Language.JA,
        'ko': Language.KO,
        'ms': Language.MS,
        'my': Language.MY,
        'pl': Language.PL,
        'pt': Language.PT,
        'ru': Language.RU,
        'th': Language.TH,
        'tr': Language.TR,
        'vi': Language.VI,
        'zh-cn': Language.ZH_CN,
        'zh-hans': Language.ZH_CN,  # 简体中文的另一种表示
        'zh-hant': Language.ZH_HANT,
        'zh-tw': Language.ZH_HANT,  # 繁体中文（台湾）
        'zh-hk': Language.ZH_HANT,  # 繁体中文（香港）
        'zh': Language.ZH_CN,  # 默认中文使用简体
    }
    
    # 先尝试完整匹配，如果没有则尝试只匹配语言部分（不含地区）
    result = lang_map.get(lang_code)
    if result:
        return result
    
    # 如果完整匹配失败，尝试只用语言代码部分（去掉地区）
    base_lang = lang_code.split('-')[0]
    return lang_map.get(base_lang, Language.EN)
