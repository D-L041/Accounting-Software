from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


FRONTEND_BUILD = Path(settings.BASE_DIR) / "frontend-dist"
PUBLIC_ASSETS = {
    "manifest.webmanifest": "application/manifest+json",
    "icon.svg": "image/svg+xml",
    "sw.js": "application/javascript; charset=utf-8",
}


def frontend_index(request):
    index_file = FRONTEND_BUILD / "index.html"
    if not index_file.is_file():
        raise Http404("The Precious SchoolBooks frontend has not been built.")
    return HttpResponse(index_file.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")


def frontend_public_asset(request, filename):
    content_type = PUBLIC_ASSETS.get(filename)
    asset = FRONTEND_BUILD / filename
    if not content_type or not asset.is_file():
        raise Http404("Frontend asset not found.")
    response = FileResponse(asset.open("rb"), content_type=content_type)
    if filename == "sw.js":
        response["Service-Worker-Allowed"] = "/"
        response["Cache-Control"] = "no-cache"
    return response
