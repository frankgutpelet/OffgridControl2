from pydantic import BaseModel
from typing import Optional

# ---------------------------
# Pydantic-Modelle
# ---------------------------

class Room(BaseModel):
    name: str
    url: Optional[str] = None
    channel: Optional[str] = None

class ConsumerBody(BaseModel):
    name: str
    mode: str




