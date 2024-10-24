from panos import panorama

from .utils import clean_url_host, get_credentials_from_env


class Panorama(panorama.Panorama):
    """
    Wrapper class for the Panorama class from pan-os-python library:
    https://pan-os-python.readthedocs.io/en/latest/readme.html#features

    Added features are:
    - hostname can be provided with and without the scheme
        - https://mydomain.com
        - mydomain.com
        - https://mydomain.com:443
      Are all valid
    """

    def __init__(
        self,
        host=None,
        api_username=None,
        api_password=None,
        api_key=None,
        port=None,
        *args,
        **kwargs,
    ):
        env_host, env_apikey = get_credentials_from_env()
        host = host or env_host
        api_key = api_key or env_apikey
        if not host:
            raise Exception("Missing Host")
        if not api_key:
            raise Exception("Missing API Key")
        host, _, _ = clean_url_host(host)
        return super().__init__(
            host, api_username, api_password, api_key, port, *args, **kwargs
        )
