import money


class Money(money.Money):
    def __truediv__(self, other):
        r = super().__truediv__(other)
        if not isinstance(r, money.Money):
            return Money(r, self.currency)
        return r
