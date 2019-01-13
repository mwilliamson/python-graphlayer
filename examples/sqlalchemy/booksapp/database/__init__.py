import sqlalchemy.orm


from .authors import Author
from .base import Base
from .books import Book


def setup(engine):
    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    author_wodehouse = Author(name="PG Wodehouse")
    author_bernières = Author(name="Louis de Bernières")
    session.add_all((author_wodehouse, author_bernières))
    session.flush()
    session.add(Book(title="Leave It to Psmith", genre="comedy", author_id=author_wodehouse.id))
    session.add(Book(title="Right Ho, Jeeves", genre="comedy", author_id=author_wodehouse.id))
    session.add(Book(title="Captain Corelli's Mandolin", genre="historical_fiction", author_id=author_bernières.id))
    session.commit()
