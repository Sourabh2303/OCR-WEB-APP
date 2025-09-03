from sqlalchemy import Column, Integer, Text, DateTime, func
from db import Base

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    line_number = Column(Integer, nullable=False)
    line_text = Column(Text, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
