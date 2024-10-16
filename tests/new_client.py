from pa_api.xmlapi import XMLApi
from pa_api.xmlapi.clients import Client

client = Client()
xmlapi = XMLApi()

# raw_traffic = client.logs._traffic()
# all_configuration = client.configuration.get('/config')

client.configuration.get_interfaces()
