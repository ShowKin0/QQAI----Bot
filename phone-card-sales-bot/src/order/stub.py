from typing import Dict, Optional


class OrderStub:
    """订单接口桩位 - 后续替换为真实订单系统对接"""

    def create_order(self, user_id: str, product_id: str,
                     customer_info: Optional[Dict] = None) -> Dict:
        # TODO: 对接真实订单系统
        return {
            "success": False,
            "message": "下单功能暂时还没接好，你可以先加我联系方式，我帮你登记～",
        }
