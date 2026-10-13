"""Project-owned compatibility for the Microsoft online speech endpoint.

Called only in the existing synthesis worker after lazy SDK import. No installed
files, proxy/TLS settings, voices, headers, DRM or cache behavior are changed.
"""

MICROSOFT_WSS = 'wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1'


def configure_endpoint(sdk):
    # The SDK reads this module global on each connection. Its trusted client
    # token is an SDK constant, never a user credential or an embedded API key.
    sdk.communicate.WSS_URL = MICROSOFT_WSS + '?Ocp-Apim-Subscription-Key=' + sdk.constants.TRUSTED_CLIENT_TOKEN
