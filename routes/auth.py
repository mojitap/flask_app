from flask import Blueprint, redirect, url_for, session
from requests_oauthlib import OAuth1Session
import os

auth = Blueprint("auth", __name__)

@auth.route("/login/google")
def login_google():
    """Googleログイン処理"""
    redirect_uri = url_for("auth.authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/authorize/google")
def authorize_google():
    """Google認証処理"""
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo").json()
    session["user"] = user_info
    return redirect(url_for("main.home"))

@auth.route("/login/twitter")
def login_twitter():
    """Twitterログイン処理"""
    twitter = OAuth1Session(
        client_key=os.getenv("TWITTER_API_KEY"),
        client_secret=os.getenv("TWITTER_API_SECRET"),
        callback_uri=url_for("auth.authorize_twitter", _external=True)
    )
    request_token_url = "https://api.twitter.com/oauth/request_token"
    response = twitter.fetch_request_token(request_token_url)
    oauth_token = response.get("oauth_token")
    return redirect(f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}")

@auth.route("/authorize/twitter")
def authorize_twitter():
    """Twitter認証処理"""
    oauth_token = request.args.get("oauth_token")
    oauth_verifier = request.args.get("oauth_verifier")

    twitter = OAuth1Session(
        client_key=os.getenv("TWITTER_API_KEY"),
        client_secret=os.getenv("TWITTER_API_SECRET"),
        resource_owner_key=oauth_token,
        verifier=oauth_verifier
    )
    access_token_url = "https://api.twitter.com/oauth/access_token"
    tokens = twitter.fetch_access_token(access_token_url)

    session["user"] = {"twitter_id": tokens.get("user_id")}
    return redirect(url_for("main.home"))
