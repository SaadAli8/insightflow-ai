class ResponseHelper:
    @staticmethod
    def deleted(count: int) -> dict:
        return {"deleted": count}
