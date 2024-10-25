import pytest
from sqlalchemy.exc import IntegrityError

from app import app
from db import Operation, db
from models.users import (User, delete_users_by_unique_constraint,
                          get_existing_users_by_unique_constraint, sync_users)


@pytest.fixture
def setup_users():
    """
    Sets up initial users in the database for testing.
    """
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                User(slack_id="U12345", name="testuser1"),
                User(slack_id="U67890", name="testuser2"),
            ]
        )
        db.session.commit()
        yield
        db.session.remove()
        db.drop_all()


def test_get_existing_users_by_unique_constraint(setup_users):
    """
    Test if existing users by unique constraint are fetched correctly.
    """
    with app.app_context():
        unique_constraints = get_existing_users_by_unique_constraint(db.session)
        assert len(unique_constraints) == 2
        assert ("U12345", "testuser1") in unique_constraints
        assert ("U67890", "testuser2") in unique_constraints


def test_delete_users_by_unique_constraint(setup_users):
    """
    Test if users are deleted based on unique constraints correctly.
    """
    with app.app_context():
        unique_constraints_to_delete = {("U12345", "testuser1")}

        delete_users_by_unique_constraint(db.session, unique_constraints_to_delete)
        db.session.commit()

        remaining_users = User.query.all()
        assert len(remaining_users) == 1
        assert remaining_users[0].slack_id == "U67890"


def test_sync_users(setup_users):
    """
    Test if users are synced correctly based on incoming Slack user list.
    """
    incoming_slack_users = [
        {"slack_id": "U12345", "name": "updateduser1"},
        {"slack_id": "U33333", "name": "newuser"},
    ]

    with app.app_context():
        synced_users = sync_users(incoming_slack_users)
        users_in_db = User.query.all()
        assert len(users_in_db) == 2

        # Ensure users are updated/inserted correctly
        updated_user = User.query.filter_by(slack_id="U12345").first()
        new_user = User.query.filter_by(slack_id="U33333").first()

        assert updated_user is not None
        assert updated_user.name == "updateduser1"

        assert new_user is not None
        assert new_user.name == "newuser"
