from .api_base import API_Base


class API_Async_Mixin(API_Base):
    def __init__(self):
        super().__init__()

    # =====================================================================================
    #                 API for monitoring and control of RE Manager

    async def status(self):
        """
        Returns status of RE Manager.
        """
        return await self.send_request(method="status")

    # =====================================================================================
    #                 API for monitoring and control of Queue

    async def add_item(self, item, *, pos=None, before_uid=None, after_uid=None):
        request_params = self._prepare_add_item(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        return await self._rm.send_request(method="queue_item_add", params=request_params)
