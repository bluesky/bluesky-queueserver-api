from .api_base import API_Base
from .item import BItem


class API_Asyncio_Mixin(API_Base):
    def __init__(self):
        self._user = "Python API User"
        self._user_group = "admin"

    async def status(self):
        """
        Returns status of RE Manager.
        """
        return await self.send_request(method="status")

    async def add_item(self, item, *, pos=None, before_uid=None, after_uid=None):
        item = item.to_dict() if isinstance(item, BItem) else item.copy()

        request_params = {"item": item}
        if pos is not None:
            request_params["pos"] = pos
        if before_uid is not None:
            request_params["before_uid"] = before_uid
        if after_uid is not None:
            request_params["after_uid"] = after_uid
        if self.pass_user_info:
            request_params["user"] = self._user
            request_params["user_group"] = self._user_group

        return await self.send_request(method="queue_item_add", params=request_params)
