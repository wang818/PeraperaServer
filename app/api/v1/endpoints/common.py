from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.support_lang import get_support_lang
import yt_dlp
import os
import tempfile

router = APIRouter()


@router.get("/support_lang")
async def get_supported_languages():
    """Get list of supported languages."""
    return get_support_lang()


@router.get("/yt_audio")
async def download_youtube_audio(url: str = "https://www.youtube.com/watch?v=GUxIotkN2zg"):
    """Download audio from YouTube video with multiple fallback strategies."""
    
    # 定义多个配置策略
    strategies = [
        {
            'name': 'android',
            'player_client': ['android'],
            'use_cookies': False,
        },
        {
            'name': 'ios',
            'player_client': ['ios'],
            'use_cookies': False,
        },
        {
            'name': 'mweb_with_cookies',
            'player_client': ['mweb'],
            'use_cookies': True,
        },
        {
            'name': 'ios_web_with_cookies',
            'player_client': ['ios', 'web'],
            'use_cookies': True,
        },
        {
            'name': 'tv_with_cookies',
            'player_client': ['tv'],
            'use_cookies': True,
        },
    ]
    
    cookies_path = os.path.join(os.path.dirname(__file__), '../../../../cookies.txt')
    cookies_exist = os.path.exists(cookies_path)
    
    last_error = None
    
    # 尝试每个策略
    for strategy in strategies:
        # 如果策略需要 cookies 但 cookies 不存在，跳过
        if strategy['use_cookies'] and not cookies_exist:
            continue
            
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, "test")
            
            # 配置 yt-dlp 选项
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'extractor_args': {
                    'youtube': {
                        'player_client': strategy['player_client'],
                    }
                },
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            
            # 添加 cookies（如果策略需要）
            if strategy['use_cookies'] and cookies_exist:
                ydl_opts['cookiefile'] = cookies_path
            
            # 下载音频
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                audio_file = filename.rsplit('.', 1)[0] + '.mp3'
            
            # 返回文件
            if os.path.exists(audio_file):
                return FileResponse(
                    audio_file,
                    media_type='audio/mpeg',
                    filename=f"{info.get('title', 'audio')}.mp3"
                )
                
        except Exception as e:
            last_error = f"{strategy['name']}: {str(e)}"
            continue
    
    # 所有策略都失败
    raise HTTPException(
        status_code=500, 
        detail=f"所有下载策略都失败。最后错误: {last_error}"
    )


