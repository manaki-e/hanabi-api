class Card:
    def __init__(self, color=None, number=None):
        self.color = color
        self.number = number

    def __str__(self):
        return f"{self.color} - {self.number}"

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash((self.color, self.number))

    def to_dict(self):
        return {"color": self.color, "number": self.number}

    def count_not_none(self):
        count = 0
        if self.color is not None:
            count += 1
        if self.number is not None:
            count += 1
        return count
