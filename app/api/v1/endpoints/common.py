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
    """Download audio from YouTube video using cobalt.tools API as fallback."""
    import httpx
    
    # 先尝试 yt-dlp (快速尝试 android 客户端)
    try:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "test")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            audio_file = filename.rsplit('.', 1)[0] + '.mp3'
        
        if os.path.exists(audio_file):
            return FileResponse(
                audio_file,
                media_type='audio/mpeg',
                filename=f"{info.get('title', 'audio')}.mp3"
            )
    except Exception as e:
        # yt-dlp 失败，使用 cobalt.tools API
        pass
    
    # 使用 cobalt.tools API
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 请求 cobalt API
            response = await client.post(
                "https://api.cobalt.tools/api/json",
                json={
                    "url": url,
                    "vCodec": "h264",
                    "vQuality": "720",
                    "aFormat": "mp3",
                    "isAudioOnly": True,
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Cobalt API 请求失败")
            
            result = response.json()
            
            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=f"Cobalt API 错误: {result.get('text')}")
            
            # 下载音频文件
            audio_url = result.get("url")
            if not audio_url:
                raise HTTPException(status_code=500, detail="未获取到音频 URL")
            
            # 下载文件
            audio_response = await client.get(audio_url)
            if audio_response.status_code != 200:
                raise HTTPException(status_code=500, detail="音频文件下载失败")
            
            # 保存到临时文件
            temp_dir = tempfile.mkdtemp()
            audio_file = os.path.join(temp_dir, "audio.mp3")
            with open(audio_file, 'wb') as f:
                f.write(audio_response.content)
            
            return FileResponse(
                audio_file,
                media_type='audio/mpeg',
                filename="audio.mp3"
            )
            
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"网络请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


