from flask import Blueprint
from firebase_admin import auth

test_bp = Blueprint("test", __name__)
@test_bp.route("/firebase-test")
def firebase_test():
    try:
        auth.list_users(1)
        return {"firebase": "working"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(debug=True)