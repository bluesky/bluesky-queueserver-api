from .api_base import API_Base, QueueBase, HistoryBase


class QueueAsync(QueueBase):
    async def add_item(self, item, *, pos=None, before_uid=None, after_uid=None):
        request_params = self._prepare_add_item(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        return await self._rm.send_request(method="queue_item_add", params=request_params)


class HistoryAsync(HistoryBase):
    ...


class API_Async_Mixin(API_Base):
    def __init__(self):
        super().__init__(queue_type=QueueAsync, history_type=HistoryAsync)

    async def status(self):
        """
        Returns status of RE Manager.
        """
        return await self.send_request(method="status")
