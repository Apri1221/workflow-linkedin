class LeadsSummaryTable:
    def __init__(self, title, columns):
        self.type = "table"
        self.title = title
        self.columns = columns

    def to_dict(self):
        columns_dict = [column.to_dict() for column in self.columns]
        return {
            "type": self.type,
            "title": self.title,
            "columns": columns_dict
        }

    def __repr__(self):
        return f"LeadsSummaryTable(title={self.title}, columns={self.columns})"