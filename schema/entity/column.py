class Column:
    def __init__(self, key, name, format):
        self.key = key
        self.name = name
        self.format = format
    
    def to_dict(self):
        return {
            "key": self.key,
            "name": self.name,
            "format": self.format
        }

    def __repr__(self):
        return f"Column(key={self.key}, name={self.name}, format={self.format})"
