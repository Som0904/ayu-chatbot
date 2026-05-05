from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from auth import get_current_user
from services.tool_service import find_hospitals

router = APIRouter()


class HospitalSearchRequest(BaseModel):
    location: str

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("location cannot be empty")
        return cleaned[:200]


@router.post("/tools/hospitals")
async def search_hospitals(
    request: HospitalSearchRequest,
    current_user: dict = Depends(get_current_user),
):
    hospitals = find_hospitals(request.location)
    return {"location": request.location, "results": hospitals, "requested_by": current_user["id"]}
