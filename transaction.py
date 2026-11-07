class Transaction:
    def __init__(self, transaction_type, amount, category, date, description=""):
        self.transaction_type = transaction_type
        self.amount = float(amount)
        self.category = category
        self.date = date
        self.description = description

    def to_dict(self):
        return {
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "category": self.category,
            "date": self.date,
            "description": self.description
        }