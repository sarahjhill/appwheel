from django.conf import settings


class FreshStaticFilesWhileBuildingMiddleware:
    """
    While building on your Mac (DEBUG on), tell the browser to check for a newer
    version of the CSS, JavaScript and icons every time, so changes show straight away.
    On the live site WhiteNoise gives each changed file a new name instead.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and request.path.startswith('/' + settings.STATIC_URL.lstrip('/')):
            response['Cache-Control'] = 'no-cache'
        return response
