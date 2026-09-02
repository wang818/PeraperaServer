from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Union

from app.core.support_lang import get_support_lang, get_support_second_lang, get_target_lang
from app.services.cos_service import cos_service, hash_filename
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.core.dependencies import get_language
from app.core.i18n import get_translation
from app.models.user import User
from app.services import quota_service
import yt_dlp
import os
import shutil
import tempfile
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/support_lang")
async def get_supported_languages():
    """Get list of supported languages."""
    return get_support_lang()


@router.get("/support_second_lang")
async def get_supported_second_languages():
    """Get list of supported second languages."""
    return get_support_second_lang()


@router.get("/target_lang")
async def get_target_languages():
    """Get list of target languages (Japanese, Korean and Cantonese)."""
    return get_target_lang()


@router.get("/yt_audio")
async def download_youtube_audio(
    url: str = "https://www.youtube.com/watch?v=GUxIotkN2zg",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language),
):
    """下载 YouTube 音频并上传到 COS。

    需要登录鉴权。下载前先查询视频时长，校验用户剩余字幕识别时长；
    时长不足直接返回 403。下载成功后才扣除对应时长（优先月卡，其次点卡）。
    同时返回通过 youtube-v2.p.rapidapi.com/video/details 获取到的视频元信息。
    """
    from app.core.config import settings

    RAPIDAPI_KEY = settings.RAPIDAPI_KEY

    # 1. 获取视频元信息（RapidAPI，可靠来源，含 video_length 时长）
    video_id = _extract_video_id(url)
    video_info = await _fetch_video_info(video_id, RAPIDAPI_KEY)

    # 2. 时长优先用 RapidAPI 的 video_length；拿不到再回退 yt-dlp
    duration_seconds = _parse_duration(video_info)
    if duration_seconds is None:
        duration_seconds = await quota_service.get_video_duration_seconds(url)
    if duration_seconds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation("video_duration_unavailable", lang),
        )

    # 3. 下载前校验时长配额（不足则抛 403，不浪费下载带宽）
    await quota_service.check_quota_available(db, current_user, duration_seconds, lang)

    # 4. 下载音频（多服务商降级）
    audio_content, audio_title = await _fetch_audio(url)

    # 5. 下载成功后才扣除时长
    await quota_service.consume_quota(db, current_user, duration_seconds)

    # 6. 上传 COS 并提交事务（优先使用视频元信息标题）
    info_title = (video_info or {}).get("title")
    result = await _upload_to_cos(audio_content, info_title or audio_title, video_info)
    await db.commit()
    return result


@router.get("/yt_info")
async def get_youtube_info(
    url: str = "https://www.youtube.com/watch?v=GUxIotkN2zg",
    current_user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
):
    """获取 YouTube 视频元信息（不含下载，不消耗配额，需登录鉴权）。

    通过 youtube-v2.p.rapidapi.com/video/details 拉取标题、作者、时长、
    播放量、描述、缩略图等公开元信息，直接返回该 JSON。
    """
    from app.core.config import settings

    api_key = settings.RAPIDAPI_KEY
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAPIDAPI_KEY 未配置，请参考 RAPIDAPI_SETUP.md 进行设置",
        )

    video_id = _extract_video_id(url)
    info, err = await _fetch_video_info(video_id, api_key, return_error=True)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=err or "获取视频元信息失败，请检查 RapidAPI 配置、订阅状态或视频 URL",
        )
    return info


async def _fetch_audio(url: str):
    """通过 RapidAPI 下载 YouTube 音频，返回 (音频字节, 标题)。

    依次尝试多个 API 服务，直到成功为止。所有方案都失败则抛 500。
    """
    from app.core.config import settings

    RAPIDAPI_KEY = settings.RAPIDAPI_KEY
    if not RAPIDAPI_KEY:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY 未配置")

    video_id = url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1]

    async with httpx.AsyncClient(timeout=120.0) as client:
        # 方案 1: YouTube MP3 API (ytjar)
        try:
            response = await client.get(
                f"https://youtube-mp36.p.rapidapi.com/dl?id={video_id}",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "youtube-mp36.p.rapidapi.com",
                },
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok" and result.get("link"):
                    audio_response = await client.get(result["link"])
                    if audio_response.status_code == 200:
                        return audio_response.content, result.get("title", "audio")
        except Exception:
            pass

        # 方案 2: YouTube to MP3 API (备用)
        try:
            response = await client.get(
                "https://youtube-mp3-downloader2.p.rapidapi.com/ytmp3/ytmp3/custom",
                params={"url": url, "quality": "192"},
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "youtube-mp3-downloader2.p.rapidapi.com",
                },
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("dlink"):
                    audio_response = await client.get(result["dlink"])
                    if audio_response.status_code == 200:
                        return audio_response.content, result.get("title", "audio")
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="所有下载方案都失败，请检查 RapidAPI 配置或视频 URL",
        )


async def _upload_to_cos(
    audio_content: bytes, title: str, video_info: Optional[dict] = None
) -> dict:
    """将音频内容上传到 COS，返回结果 dict（含视频元信息）。"""
    temp_dir = tempfile.mkdtemp()
    try:
        safe_title = hash_filename(title, fallback="audio")
        file_name = f"{safe_title}.mp3"
        audio_file = os.path.join(temp_dir, file_name)
        with open(audio_file, "wb") as f:
            f.write(audio_content)

        object_key = cos_service.generate_object_key(file_name)
        cos_url = await cos_service.upload_file(audio_file, object_key)

        return {
            "status": "ok",
            "title": title,
            "url": cos_url,
            "object_key": object_key,
            "content_type": "audio/mpeg",
            "video_info": video_info,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def _fetch_video_info(
    video_id: str, api_key: Optional[str], return_error: bool = False
) -> Union[tuple, Optional[dict]]:
    """通过 youtube-v2.p.rapidapi.com/video/details 获取视频元信息。

    返回字段示例：title / author / number_of_views / video_length / description /
    published_time / thumbnails 等。
    - 默认（return_error=False）：最佳努力，key 未配置或请求失败时返回 None，
      不影响主下载与计费流程。
    - return_error=True：失败时返回 (None, 错误说明)，供独立元信息接口向调用方
      暴露真实失败原因，便于排查。
    """
    if not api_key:
        err = "RAPIDAPI_KEY 未配置"
        return (None, err) if return_error else None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://youtube-v2.p.rapidapi.com/video/details",
                params={"video_id": video_id},
                headers={
                    "X-RapidAPI-Key": api_key,
                    "X-RapidAPI-Host": "youtube-v2.p.rapidapi.com",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return (data, None) if return_error else data
            err = f"RapidAPI 返回状态码 {resp.status_code}，响应: {resp.text[:300]}"
            logger.warning(f"获取视频元信息失败: {err}")
            return (None, err) if return_error else None
    except Exception as e:
        err = f"请求 RapidAPI 异常: {e}"
        logger.warning(f"获取视频元信息异常: {err}")
        return (None, err) if return_error else None


def _extract_video_id(url: str) -> str:
    """从 YouTube URL 中提取视频 ID"""
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    elif "/shorts/" in url:
        return url.split("/shorts/")[-1].split("?")[0]
    return url.split("/")[-1]


def _parse_duration(video_info: Optional[dict]) -> Optional[int]:
    """从 RapidAPI 视频元信息中提取时长（秒）。

    youtube-v2 的 video_length 为秒数（字符串或数字）。解析失败返回 None，
    由调用方回退到 yt-dlp 或报错。
    """
    if not video_info:
        return None
    raw = video_info.get("video_length")
    if raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


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
                formats = result.get("formats", [])
                download_url = None
                title = result.get("title", "video")

                for fmt in sorted(formats, key=lambda x: x.get("height", 0) or 0, reverse=True):
                    if fmt.get("url") and fmt.get("ext") == "mp4" and fmt.get("acodec") != "none":
                        download_url = fmt["url"]
                        break

                if not download_url:
                    for fmt in formats:
                        if fmt.get("url") and fmt.get("ext") == "mp4":
                            download_url = fmt["url"]
                            break

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

        raise HTTPException(
            status_code=500,
            detail="所有视频下载方案都失败了，请检查 RapidAPI 配置、API 订阅状态或视频 URL 是否正确",
        )
