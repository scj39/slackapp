from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    tuple_,
)
from sqlalchemy.dialects.postgresql import insert

from db import Operation, db


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    slack_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    # compound index on slack_id and name
    __table_args__ = (
        Index(
            "idx_slack_id_name",
            "slack_id",
            "name",
            unique=True,
        ),
    )


def get_existing_users_by_unique_constraint(session) -> set[tuple[str, str]]:
    """
    Returns all users by unique constraint
    """
    if not session:
        raise ValueError("Need valid session to run queries")
    results = session.query(User.slack_id, User.name).all()
    return set(results)


def delete_users_by_unique_constraint(
    session, unique_constraint_pairs: set[tuple[str, str]]
) -> None:
    """
    Deletes all users that match the set of unique constraints
    """
    session.query(User).filter(
        tuple_(User.slack_id, User.name).in_(unique_constraint_pairs)
    ).delete(synchronize_session=False)


def sync_users(slack_users: list[dict]) -> Optional[set[tuple[str, str]]]:
    """Syncs users. Deletes users that exist only on the app (and not in the corresponding
    Slack workspace.
    """
    slack_users = [user for user in slack_users if user]
    with Operation.begin() as transaction:
        upsert_time = func.now()
        insertion = insert(User.__table__).values(
            slack_users,
        )
        upsert = insertion.on_conflict_do_update(
            index_elements=["slack_id", "name"], set_={"updated_at": upsert_time}
        )
        transaction.execute(upsert)
        transaction.execute(
            User.__table__.delete().where(User.updated_at < upsert_time)
        )
        return get_existing_users_by_unique_constraint(transaction)
