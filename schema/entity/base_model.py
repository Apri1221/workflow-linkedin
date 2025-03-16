from sqlalchemy import Column, TIMESTAMP, String
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from utils.uuid import str_of_uuid7
# https://stackoverflow.com/questions/183042/how-can-i-use-uuids-in-sqlalchemy


Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    id = Column(String(36), primary_key=True, nullable=False, index=True, default=str_of_uuid7, server_default="uuid_generate_v4()")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())