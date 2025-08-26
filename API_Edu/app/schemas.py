from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, example="John Doe")
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", example="john@example.com")
    age: int = Field(..., gt=0, le=120, example=30)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.replace(' ', '').isalpha():
            raise ValueError('Name should contain only letters and spaces')
        return v

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int

    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    detail: str
    error_type: str

class ValidationErrorResponse(BaseModel):
    detail: str
    error_type: str
    errors: List[dict]