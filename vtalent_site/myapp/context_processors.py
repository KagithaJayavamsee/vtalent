from django.conf import settings


def neon_realtime(request):
    return {
        'neon_realtime_url': settings.NEON_REALTIME_URL,
        'realtime_api_url': settings.REALTIME_API_URL,
    }
