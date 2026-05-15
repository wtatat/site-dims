from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from .db_session import SqlAlchemyBase


class Track(SqlAlchemyBase):
    __tablename__ = "tracks"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String, nullable=False)
    filename = sa.Column(sa.String, nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="tracks")
