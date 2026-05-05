from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Lutfen once giris yapin.", "danger")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped
