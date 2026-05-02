import time
from src.session.manager import SessionManager


def test_get_or_create_creates_new_session():
    mgr = SessionManager()
    session = mgr.get_or_create("user_1")
    assert session.user_id == "user_1"
    assert session.messages == []


def test_get_or_create_returns_existing_session():
    mgr = SessionManager()
    s1 = mgr.get_or_create("user_1")
    s2 = mgr.get_or_create("user_1")
    assert s1 is s2


def test_add_message_appends_and_trims():
    mgr = SessionManager(max_rounds=2)
    mgr.add_message("user_1", "user", "hi")
    mgr.add_message("user_1", "assistant", "hello")
    mgr.add_message("user_1", "user", "how r u")
    mgr.add_message("user_1", "assistant", "good")
    mgr.add_message("user_1", "user", "third round")
    history = mgr.get_history("user_1")
    assert len(history) == 4
    assert history[0]["content"] == "hello"


def test_is_first_interaction():
    mgr = SessionManager()
    assert mgr.is_first_interaction("new_user") is True
    mgr.add_message("new_user", "user", "hello")
    assert mgr.is_first_interaction("new_user") is False


def test_clear_removes_session():
    mgr = SessionManager()
    mgr.get_or_create("user_1")
    mgr.clear("user_1")
    assert mgr.is_first_interaction("user_1") is True


def test_expired_session_is_cleaned():
    mgr = SessionManager(expire_minutes=0)
    mgr.get_or_create("user_1")
    time.sleep(0.1)
    assert mgr.is_first_interaction("user_1") is True
