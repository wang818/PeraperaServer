from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from app.core.support_lang import get_support_lang
from app.services.cos_service import cos_service, hash_filename
import yt_dlp
import os
import shutil
import tempfile
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/support_lang")
async def get_supported_languages():
    """Get list of supported languages."""
    return get_support_lang()


@router.get("/yt_audio")
async def download_youtube_audio(url: str = "https://www.youtube.com/watch?v=GUxIotkN2zg"):
    """Download audio from YouTube video using RapidAPI and upload to COS."""
    import httpx
    from app.core.config import settings

    # 从配置获取 RapidAPI Key
    RAPIDAPI_KEY = settings.RAPIDAPI_KEY
    if not RAPIDAPI_KEY:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY 未配置")

    # 提取视频 ID
    video_id = url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1]

    async def _upload_to_cos(audio_content: bytes, title: str) -> dict:
        """将音频内容上传到 COS，返回结果 dict。"""
        temp_dir = tempfile.mkdtemp()
        try:
            safe_title = hash_filename(title, fallback="audio")
            file_name = f"{safe_title}.mp3"
            audio_file = os.path.join(temp_dir, file_name)
            with open(audio_file, 'wb') as f:
                f.write(audio_content)

            object_key = cos_service.generate_object_key(file_name)
            cos_url = await cos_service.upload_file(audio_file, object_key)

            return {
                "status": "ok",
                "title": title,
                "url": cos_url,
                "object_key": object_key,
                "content_type": "audio/mpeg",
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

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
                        audio_url = result["link"]
                        audio_response = await client.get(audio_url)

                        if audio_response.status_code == 200:
                            return await _upload_to_cos(
                                audio_response.content,
                                result.get('title', 'audio'),
                            )
            except Exception as e:
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
                        audio_url = result["dlink"]
                        audio_response = await client.get(audio_url)

                        if audio_response.status_code == 200:
                            return await _upload_to_cos(
                                audio_response.content,
                                result.get('title', 'audio'),
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




def _extract_video_id(url: str) -> str:
    """从 YouTube URL 中提取视频 ID"""
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    elif "/shorts/" in url:
        return url.split("/shorts/")[-1].split("?")[0]
    return url.split("/")[-1]


@router.get("/yt_video")
async def download_youtube_video(url: str = "https://www.youtube.com/watch?v=YGG2LlxlvJI"):
    """
    通过第三方 RapidAPI 下载 YouTube 视频（MP4 格式）。
    
    依次尝试多个 API 服务，直到成功为止：
    1. YouTube Downloader (FAST) - POST /download
    2. YouTube Video & Playlist Downloader - GET /video
    3. YouTube MP3 Audio Video Downloader (nikzeferis) - GET /dl
    """
    import httpx
    from app.core.config import settings

    RAPIDAPI_KEY = settings.RAPIDAPI_KEY
    if not RAPIDAPI_KEY:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY 未配置，请参考 RAPIDAPI_SETUP.md 进行设置")

    video_id = _extract_video_id(url)
    logger.info(f"开始下载视频, video_id={video_id}, url={url}")

    async with httpx.AsyncClient(timeout=180.0) as client:

        # ── 方案 1: YouTube Downloader (FAST) ──
        try:
            logger.info("尝试方案 1: youtube-downloader-fast")
            response = await client.post(
                "https://youtube-downloader-fast.p.rapidapi.com/download",
                json={"url": url, "format": "mp4"},
                headers={
                    "Content-Type": "application/json",
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "youtube-downloader-fast.p.rapidapi.com",
                },
            )
            if response.status_code == 200:
                result = response.json()
                download_url = result.get("download_url") or result.get("link")
                title = result.get("title", "video")
                if download_url:
                    logger.info(f"方案 1 成功, title={title}")
                    video_resp = await client.get(download_url, follow_redirects=True)
                    if video_resp.status_code == 200:
                        temp_dir = tempfile.mkdtemp()
                        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "video"
                        video_file = os.path.join(temp_dir, f"{safe_title}.mp4")
                        with open(video_file, "wb") as f:
                            f.write(video_resp.content)
                        return FileResponse(
                            video_file,
                            media_type="video/mp4",
                            filename=f"{safe_title}.mp4",
                        )
        except Exception as e:
            logger.warning(f"方案 1 失败: {e}")

        # ── 方案 2: YouTube Video & Playlist Downloader ──
        try:
            logger.info("尝试方案 2: youtube-video-playlist-downloader")
            response = await client.get(
                "https://youtube-video-playlist-downloader.p.rapidapi.com/video",
                params={"video_id": video_id, "resolution": "mp4"},
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "youtube-video-playlist-downloader.p.rapidapi.com",
                },
            )
            if response.status_code == 200:
                result = response.json()
                # 该 API 返回 formats 列表，选择包含视频+音频的 mp4
                formats = result.get("formats", [])
                download_url = None
                title = result.get("title", "video")

                # 优先选择有音频的 mp4 格式，分辨率尽量高
                for fmt in sorted(formats, key=lambda x: x.get("height", 0) or 0, reverse=True):
                    if fmt.get("url") and fmt.get("ext") == "mp4" and fmt.get("acodec") != "none":
                        download_url = fmt["url"]
                        break

                # 如果没有带音频的，退而求其次选任意 mp4
                if not download_url:
                    for fmt in formats:
                        if fmt.get("url") and fmt.get("ext") == "mp4":
                            download_url = fmt["url"]
                            break

                # 有些 API 直接返回 link / download_url
                if not download_url:
                    download_url = result.get("link") or result.get("download_url")

                if download_url:
                    logger.info(f"方案 2 成功, title={title}")
                    video_resp = await client.get(download_url, follow_redirects=True)
                    if video_resp.status_code == 200:
                        temp_dir = tempfile.mkdtemp()
                        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "video"
                        video_file = os.path.join(temp_dir, f"{safe_title}.mp4")
                        with open(video_file, "wb") as f:
                            f.write(video_resp.content)
                        return FileResponse(
                            video_file,
                            media_type="video/mp4",
                            filename=f"{safe_title}.mp4",
                        )
        except Exception as e:
            logger.warning(f"方案 2 失败: {e}")

        # ── 方案 3: YouTube MP3 Audio Video Downloader (nikzeferis) ──
        try:
            logger.info("尝试方案 3: youtube-mp3-audio-video-downloader")
            response = await client.get(
                "https://youtube-mp3-audio-video-downloader.p.rapidapi.com/dl",
                params={"id": video_id},
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "youtube-mp3-audio-video-downloader.p.rapidapi.com",
                },
            )
            if response.status_code == 200:
                result = response.json()
                title = result.get("title", "video")
                # 该 API 返回 formats / adaptiveFormats
                formats = result.get("formats", []) + result.get("adaptiveFormats", [])
                download_url = None

                for fmt in sorted(formats, key=lambda x: x.get("height", 0) or 0, reverse=True):
                    if fmt.get("url") and "video" in (fmt.get("mimeType", "")):
                        download_url = fmt["url"]
                        break

                if not download_url:
                    download_url = result.get("link") or result.get("download_url")

                if download_url:
                    logger.info(f"方案 3 成功, title={title}")
                    video_resp = await client.get(download_url, follow_redirects=True)
                    if video_resp.status_code == 200:
                        temp_dir = tempfile.mkdtemp()
                        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "video"
                        video_file = os.path.join(temp_dir, f"{safe_title}.mp4")
                        with open(video_file, "wb") as f:
                            f.write(video_resp.content)
                        return FileResponse(
                            video_file,
                            media_type="video/mp4",
                            filename=f"{safe_title}.mp4",
                        )
        except Exception as e:
            logger.warning(f"方案 3 失败: {e}")

        # ── 所有方案都失败 ──
        raise HTTPException(
            status_code=500,
            detail="所有视频下载方案都失败了，请检查 RapidAPI 配置、API 订阅状态或视频 URL 是否正确",
        )
