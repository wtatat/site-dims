import base64
import hashlib
import hmac
import secrets

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from .db_session import SqlAlchemyBase


followers_table = sa.Table(
    "followers",
    SqlAlchemyBase.metadata,
    sa.Column("follower_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
    sa.Column("followed_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
)


class User(SqlAlchemyBase):
    __tablename__ = "users"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String, unique=True, nullable=False)
    email = sa.Column(sa.String, unique=True, index=True, nullable=False)
    hashed_password = sa.Column(sa.String, nullable=False)
    avatar_filename = sa.Column(sa.String, nullable=True)

    following = relationship(
        "User",
        secondary=followers_table,
        primaryjoin=id == followers_table.c.follower_id,
        secondaryjoin=id == followers_table.c.followed_id,
        backref="followers",
    )
    tracks = relationship(
        "Track",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Track.created_at)",
    )

    def set_password(self, password):
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100000,
        )
        self.hashed_password = (
            f"{base64.b64encode(salt).decode('ascii')}$"
            f"{base64.b64encode(password_hash).decode('ascii')}"
        )

    def check_password(self, password):
        try:
            salt_b64, hash_b64 = self.hashed_password.split("$", 1)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            saved_hash = base64.b64decode(hash_b64.encode("ascii"))
        except (ValueError, TypeError):
            return False

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100000,
        )
        return hmac.compare_digest(password_hash, saved_hash)

    def is_following(self, user):
        return any(followed.id == user.id for followed in self.following)
