import requests
from cryptography.fernet import Fernet
from flask import (
    Flask,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_restful import Api, Resource

from config import Config
from db import db
from models.users import sync_users

# set up Flask app
app = Flask(__name__)
api = Api(app)
app.config.from_object(Config)
cipher = Fernet(app.config["ENCRYPTION_KEY"])
db.init_app(app)
with app.app_context():
    db.create_all()


class Login(Resource):
    def get(self):
        CLIENT_ID, OAUTH_REDIRECT_URI = app.config.get(
            "CLIENT_ID", None
        ), app.config.get("OAUTH_REDIRECT_URI", None)
        if CLIENT_ID and OAUTH_REDIRECT_URI:
            slack_auth_url = (
                f"https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&user_scope=users:read"
                f"&redirect_uri={OAUTH_REDIRECT_URI}"
            )
            return redirect(slack_auth_url)
        return "Unauthorized access detected", 429


class OAuthCallback(Resource):
    def get(self):
        """
        Gets access token from Slack OAuth response
        """
        CLIENT_ID, OAUTH_REDIRECT_URI = app.config.get(
            "CLIENT_ID", None
        ), app.config.get("OAUTH_REDIRECT_URI", None)
        CLIENT_SECRET = app.config.get("CLIENT_SECRET", None)
        code = request.args.get("code")
        oauth_response = requests.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": OAUTH_REDIRECT_URI,
            },
        ).json()

        access_token = oauth_response.get("authed_user", {}).get("access_token", None)
        if not access_token:
            return {"error": "Could not retrieve access token"}, 400
        session["access_token"] = cipher.encrypt(access_token.encode()).decode()
        return redirect(url_for("users"))


class ListUsers(Resource):
    def get(self):
        """
        Syncs database with Slack workspace user list and renders all users in
        workspace in table
        """
        # get & decrypt access token
        access_token = session.get("access_token")
        if not access_token:
            return redirect(url_for("login"))
        access_token = cipher.decrypt(access_token.encode()).decode()
        # send access token over the wire
        response = requests.get(
            "https://slack.com/api/users.list",
            headers={"Authorization": f"Bearer {access_token}"},
        ).json()
        if not response.get("ok") and response.get("error", "") == "ratelimited":
            return {"error": "Rate limited by Slack. Slow down!"}, 429
        if not response.get("ok"):
            return {"error": "Unable to fetch users"}, 400
        # process response
        users = response.get("members", [])
        alias_team = lambda x: "slack_id" if x == "team_id" else x
        slack_users = [
            {
                alias_team(k): user[k]
                for k in ["team_id", "name"]
                if (k in user and not user.get("deleted", False))
            }
            for user in users
        ]
        list_users = [
            {"slack_id": slack_id, "name": name}
            for slack_id, name in sync_users(slack_users)
        ]
        # send back users to view
        response = make_response(
            render_template("list_users.html", list_users=list_users)
        )
        response.headers["Content-Type"] = "text/html"
        return response


# define API routes
api.add_resource(Login, "/login", endpoint="login")
api.add_resource(OAuthCallback, "/oauth/callback")
api.add_resource(ListUsers, "/users", endpoint="users")

if __name__ == "__main__":
    app.run(debug=False)
