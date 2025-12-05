from datetime import datetime


class SeasonalAnalyzer:
    def __init__(self):
        self.seasonal_patterns = {
            "electronics": {"best_month": 11, "worst_month": 3, "discount": 15},
            "clothing": {"best_month": 1, "worst_month": 5, "discount": 30},
            "home": {"best_month": 8, "worst_month": 12, "discount": 20},
            "books": {"best_month": 4, "worst_month": 8, "discount": 25},
            "sports": {"best_month": 12, "worst_month": 6, "discount": 18},
        }

    def predict_best_purchase_time(self, product_name, category):
        current_month = datetime.now().month
        pattern = self.seasonal_patterns.get(
            category, {"best_month": 1, "worst_month": 6, "discount": 10}
        )

        months_to_wait = (pattern["best_month"] - current_month) % 12
        if months_to_wait < 0:
            months_to_wait += 12

        return {
            "best_month": pattern["best_month"],
            "months_to_wait": months_to_wait,
            "expected_discount": pattern["discount"],
            "recommendation": self.generate_recommendation(
                months_to_wait, pattern["discount"]
            ),
        }

    def generate_recommendation(self, months_to_wait, discount):
        if months_to_wait == 0:
            return "Сейчас лучший момент для покупки! Уже можно ловить скидку."
        if months_to_wait <= 2:
            return f"Подождите {months_to_wait} месяцев, скидка может достигнуть {discount}%."
        return (
            f"Выгодный период будет через примерно {months_to_wait} месяцев. "
            "Следите за динамикой."
        )
