from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def service_status():
    """Return service status.

    Returns ``{"status": true}`` to indicate the API is up and responding.
    """
    return {"status": True}
