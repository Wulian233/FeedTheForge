class FTBException(Exception):
    def __init__(self, path, status, message):
        super().__init__(f"FTB API failed at {path}: {status} {message or ''}".strip())
        self.path = path
        self.status = status
        self.message = message
