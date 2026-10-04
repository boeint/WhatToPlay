from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.deps import SessionDep
from app.preferences import DEFAULT_AI_INSTRUCTIONS, all_preferences, set_preferences

router = APIRouter(tags=["settings"])


class SettingsOut(BaseModel):
    ai_enabled: bool
    ai_instructions: str
    default_ai_instructions: str      # read-only: to offer "reset to default"


class SettingsUpdate(BaseModel):
    """Send only what changes."""
    model_config = ConfigDict(extra="forbid")

    ai_enabled: bool = None
    ai_instructions: str = Field(None, max_length=20000)


@router.get("/api/settings", response_model=SettingsOut)
def get_settings_(session: SessionDep):
    return {**all_preferences(session), "default_ai_instructions": DEFAULT_AI_INSTRUCTIONS}


@router.patch("/api/settings", response_model=SettingsOut)
def update_settings(data: SettingsUpdate, session: SessionDep):
    set_preferences(session, data.model_dump(exclude_unset=True))
    return {**all_preferences(session), "default_ai_instructions": DEFAULT_AI_INSTRUCTIONS}
