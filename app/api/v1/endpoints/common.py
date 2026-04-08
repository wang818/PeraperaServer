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
    """Download audio from YouTube video using RapidAPI."""
    import httpx
    from app.core.config import settings
    
    # 从配置获取 RapidAPI Key
    RAPIDAPI_KEY = settings.RAPIDAPI_KEY
    if not RAPIDAPI_KEY:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY 未配置")
    
    # 提取视频 ID
    video_id = url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1]
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 方案 1: YouTube MP3 API (ytjar)
            try:
                response = await client.get(
                    f"https://youtube-mp36.p.rapidapi.com/dl?id={video_id}",
                    headers={
                        "X-RapidAPI-Key": RAPIDAPI_KEY,
                        "X-RapidAPI-Host": "youtube-mp36.p.rapidapi.com"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "ok" and result.get("link"):
                        # 下载 MP3 文件
                        audio_url = result["link"]
                        audio_response = await client.get(audio_url)
                        
                        if audio_response.status_code == 200:
                            # 保存到临时文件
                            temp_dir = tempfile.mkdtemp()
                            audio_file = os.path.join(temp_dir, f"{result.get('title', 'audio')}.mp3")
                            with open(audio_file, 'wb') as f:
                                f.write(audio_response.content)
                            
                            return FileResponse(
                                audio_file,
                                media_type='audio/mpeg',
                                filename=f"{result.get('title', 'audio')}.mp3"
                            )
            except Exception as e:
                # 方案 1 失败，尝试方案 2
                pass
            
            # 方案 2: YouTube to MP3 API (备用)
            try:
                response = await client.get(
                    "https://youtube-mp3-downloader2.p.rapidapi.com/ytmp3/ytmp3/custom",
                    params={
                        "url": url,
                        "quality": "192"
                    },
                    headers={
                        "X-RapidAPI-Key": RAPIDAPI_KEY,
                        "X-RapidAPI-Host": "youtube-mp3-downloader2.p.rapidapi.com"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("dlink"):
                        # 下载 MP3 文件
                        audio_url = result["dlink"]
                        audio_response = await client.get(audio_url)
                        
                        if audio_response.status_code == 200:
                            # 保存到临时文件
                            temp_dir = tempfile.mkdtemp()
                            audio_file = os.path.join(temp_dir, f"{result.get('title', 'audio')}.mp3")
                            with open(audio_file, 'wb') as f:
                                f.write(audio_response.content)
                            
                            return FileResponse(
                                audio_file,
                                media_type='audio/mpeg',
                                filename=f"{result.get('title', 'audio')}.mp3"
                            )
            except Exception as e:
                pass
            
            # 所有方案都失败
            raise HTTPException(
                status_code=500, 
                detail="所有下载方案都失败，请检查 RapidAPI 配置或视频 URL"
            )
            
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"网络请求失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


