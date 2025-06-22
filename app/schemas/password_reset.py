from pydantic import BaseModel,EmailStr,StringConstraints
from typing import Annotated

class ForgotPasswordRequest(BaseModel):
    email:EmailStr


class ResetPasswordRequest(BaseModel):
    token:str
    new_password: Annotated[str, StringConstraints(min_length=6)]