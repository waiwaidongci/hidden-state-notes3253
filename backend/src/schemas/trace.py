from pydantic import BaseModel,Field,ConfigDict
from typing import Annotated
ConstraintStep=Annotated[int,Field(gt=0,strict=True)]
ConstraintState=Annotated[int,Field(strict=True)]
class MomentConstraint(BaseModel):
 # 待核对的隐态假设：该时刻只允许这些0-based状态索引；其余时刻不设限制。
 model_config=ConfigDict(extra='forbid')
 step:ConstraintStep
 allowed_states:list[ConstraintState]=Field(min_length=1,max_length=5)
class TraceInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
 reference:str=Field(min_length=1,max_length=100)
 tokens:list[str]=Field(min_length=1,max_length=200)
 constraints:list[MomentConstraint]=Field(default_factory=list,max_length=200)
class TracePatch(BaseModel):
 model_config=ConfigDict(extra='forbid')
 tokens:list[str]|None=Field(default=None,min_length=1,max_length=200)
 constraints:list[MomentConstraint]|None=Field(default=None,max_length=200)
