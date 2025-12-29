"""
Auth Blueprint - Login/Logout Routes
=====================================

PIN-based authentication for RentasClaras.
"""

import os
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for


auth_bp = Blueprint("auth", __name__)

# PIN from environment
RENTASCLARAS_PIN = os.environ.get("RENTASCLARAS_PIN")


def login_required(f):
    """Decorator to require PIN authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Simple PIN login for password protection."""
    error = None

    if request.method == "POST":
        pin = request.form.get("pin", "")
        if pin == RENTASCLARAS_PIN:
            session["authenticated"] = True
            return redirect(url_for("pagos.index"))
        else:
            error = "PIN incorrecto. Intente de nuevo."

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    """Clear the session and log out."""
    session.clear()
    return redirect(url_for("auth.login"))
