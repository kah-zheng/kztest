from app import app as flask_app

def test_root_ok():
    with flask_app.test_client() as c:
        r = c.get("/")
        assert r.status_code == 200
        assert b"Hello" in r.data  # matches the Flask response text

