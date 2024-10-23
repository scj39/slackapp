from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    Index,
    tuple_,
)
from db import db, Operation
from typing import Optional


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    slack_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True))
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
    TODO: Instead of fetching all users and then adding/deleting, perform an upsert and
    then delete all entries that haven't just been modified for better scalability
    """
    latest_slack_users, users_for_deletion = set(), None
    with Operation.begin() as transaction:
        existing_users = get_existing_users_by_unique_constraint(transaction)
        for user in slack_users:
            if not user.get("deleted", True):
                latest_slack_users.add((user["id"], user["real_name"]))
                if (user["id"], user["real_name"]) not in existing_users:
                    transaction.add(User(slack_id=user["id"], name=user["real_name"]))
        users_for_deletion = existing_users - latest_slack_users
        if users_for_deletion:
            delete_users_by_unique_constraint(transaction, users_for_deletion)
        existing_users = get_existing_users_by_unique_constraint(transaction)
        return existing_users
