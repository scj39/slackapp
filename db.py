import os
from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()


class Operation:
    @classmethod
    @contextmanager
    def begin(cls, session=None):
        session = session or db.session
        try:
            with session.begin():
                yield session
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            if session is not db.session:
                session.close()
