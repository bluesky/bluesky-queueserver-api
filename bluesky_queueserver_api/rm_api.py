class API_Threads_Mixin:
    def __init__(self):
        pass

    def status(self):
        """
        Returns status of RE Manager.
        """
        return self.send_request(method="status")
