import os
try:
    # os environment variables from Heroku
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]
    email_username = os.environ["email_username"]
    email_password = os.environ["email_password"]
except Exception:
    from .creds import SECRET_KEY, SQLALCHEMY_DATABASE_URI, email_username, email_password


class Config:
    SECRET_KEY = SECRET_KEY
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = email_username
    MAIL_PASSWORD = email_password
