from pa_api.xmlapi import XMLApi
from pa_api.xmlapi.clients import Client
from pa_api.xmlapi.utils import pprint  # noqa: F401

client = Client()
xmlapi = XMLApi()

# raw_traffic = client.logs._traffic()
# all_configuration = client.configuration.get('/config')

# key = client.generate_apikey("gallay", getpass("Enter you password: "))
# print(key)

client.configuration.get_interfaces()
