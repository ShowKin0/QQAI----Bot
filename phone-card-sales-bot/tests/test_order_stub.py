from src.order.stub import OrderStub


def test_create_order_returns_placeholder():
    stub = OrderStub()
    result = stub.create_order("user_1", "campus_card")
    assert result["success"] is False
    assert "下单功能" in result["message"]


def test_create_order_accepts_customer_info():
    stub = OrderStub()
    result = stub.create_order("user_1", "campus_card",
                                customer_info={"name": "test"})
    assert result["success"] is False
