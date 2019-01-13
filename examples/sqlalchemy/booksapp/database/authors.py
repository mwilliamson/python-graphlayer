import sqlalchemy

from .base import Base


class Author(Base):
    __tablename__ = "author"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
