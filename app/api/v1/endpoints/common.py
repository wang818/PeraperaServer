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
    """Download audio from YouTube video."""
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "test")
        
        # 配置 yt-dlp 选项 - 使用 mweb 客户端配合 cookies
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'extractor_args': {
                'youtube': {
                    'player_client': ['mweb'],  # 移动网页客户端
                }
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        # cookies 文件路径
        cookies_path = os.path.join(os.path.dirname(__file__), '../../../../cookies.txt')
        if os.path.exists(cookies_path):
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
        else:
            raise HTTPException(status_code=500, detail="音频文件生成失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


