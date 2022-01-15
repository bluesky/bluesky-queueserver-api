class API_Asyncio_Mixin:
    def __init__(self):
        pass

    async def status(self):
        """
        Returns status of RE Manager.
        """
        return await self.send_request(method="status")
