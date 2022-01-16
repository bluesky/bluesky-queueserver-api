from .api_base import API_Base, QueueBase, HistoryBase


class QueueThreads(QueueBase):
    def add_item(self, item, *, pos=None, before_uid=None, after_uid=None):
        request_params = self._prepare_add_item(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        return self._rm.send_request(method="queue_item_add", params=request_params)


class HistoryThreads(HistoryBase):
    ...


class API_Threads_Mixin(API_Base):
    def __init__(self):
        super().__init__(queue_type=QueueThreads, history_type=HistoryThreads)

    def status(self):
        """
        Returns status of RE Manager.
        """
        return self.send_request(method="status")
