from typing import List
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_snake
from utils.constant import StaticValue


# https://medium.com/@drewscatterday/convert-fastapi-snake-case-json-response-to-camel-case-d94c20e92b52

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        # alias_generator=to_snake,
        populate_by_name=True,
        from_attributes=True,
    )

class CommonHeaders(BaseModel):
    host: str | None = None
    sessionId: str | None = None


class CookiesRequest(BaseSchema):
    key: str
    value: str
    domain: str
    path: str
    hostOnly: bool
    creation: str
    lastAccessed: str
    sameSite: str
    expires: str
    secure: bool
    httpOnly: bool


class PromptRequest(BaseSchema):
    jobTitle: str
    numberOfLeads: int
    seniorityLevel: List[str]
    industry: str
    yearsOfExperience: int
    goodToHave: str

    @field_validator('jobTitle')
    def check_job_title(cls, v: str) -> str:
        if v.strip() == '' or v == None:
            raise ValueError('field `jobTitle` required')
        return v

    @field_validator('numberOfLeads')
    def check_positive_number_of_leads(cls, v: str) -> str:
        if v < 0:
            raise ValueError('field `numberOfLeads` must be a positive integer')
        elif v == None:
            raise ValueError('field `numberOfLeads` required')
        return v
    
    @field_validator('yearsOfExperience')
    def check_positive_years_of_experience(cls, v: str) -> str:
        if v < 0:
            raise ValueError('field `yearsOfExperience` must be a positive integer')
        elif v == None:
            raise ValueError('field `yearsOfExperience` required')
        return v
    
    @field_validator('goodToHave')
    def check_good_to_have(cls, v: str) -> str:
        if v == None:
            raise ValueError('goodToHave required')
        return v
    
    @field_validator('seniorityLevel')
    def check_seniority_level(cls, v: List[str]) -> List[str]:
        if v == None:
            raise ValueError('field `seniorityLevel` required')
    
        allowed_values = StaticValue().SENIORITY_LEVEL.keys()
        allowed_lower_map = {value.lower(): value for value in allowed_values}
        invalid_levels = []
        valid_levels = []
        
        for level in v:
            lower_level = level.lower()
            if lower_level in allowed_lower_map:
                valid_levels.append(allowed_lower_map[lower_level])
            else:
                invalid_levels.append(level)
        
        if invalid_levels:
            allowed_str = ", ".join(allowed_values)
            raise ValueError(
                f"Invalid value `{', '.join(invalid_levels)}` on `seniorityLevel` field - "
                f"Allowed values: {allowed_str}"
            )
        
        return valid_levels
    


class LeadFilterRequest(BaseSchema):
    sessionId: str

class SearchLeadRequest(BaseSchema):
    jobTitle: str
    numberOfLeads: int
    seniorityLevel: List[str]
    companyHeadcount: List[str]
    functions: List[str]
    yearsOfExperience: List[str]
    goodToHave: str
    