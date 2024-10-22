class ServerError(Exception):
    pass


class ClientNotBoundError(Exception):
    def __init__(
        self, message="Model is not bound to a client instance", *args: object
    ) -> None:
        super().__init__((message, *args))
