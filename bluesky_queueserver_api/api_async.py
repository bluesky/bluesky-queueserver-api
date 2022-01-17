from .api_base import API_Base, QueueBase, HistoryBase, ManagerBase, EnvironmentBase, RunEngineBase


class QueueAsync(QueueBase):
    async def add_item(self, item, *, pos=None, before_uid=None, after_uid=None):
        request_params = self._prepare_add_item(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        return await self._rm.send_request(method="queue_item_add", params=request_params)


class HistoryAsync(HistoryBase):
    ...


class ManagerAsync(ManagerBase):
    ...


class EnvironmentAsync(EnvironmentBase):
    ...


class RunEngineAsync(RunEngineBase):
    ...


class API_Async_Mixin(API_Base):
    def __init__(self):
        super().__init__(
            queue_type=QueueAsync,
            history_type=HistoryAsync,
            manager_type=ManagerAsync,
            environment_type=EnvironmentAsync,
            run_engine_type=RunEngineAsync,
        )

    async def status(self):
        """
        Returns status of RE Manager.
        """
        return await self.send_request(method="status")
