import logging
from urllib.parse import urlencode

import requests
import urllib3
from django.core.cache import cache
from requests import Request, Response

logger = logging.getLogger(__name__)


class BasisService:
    _api_base_url = None
    _timeout: tuple[int, ...] = (5, 10)
    _api_path: str = "/api/v1"

    class BasisUrlFout(Exception):
        ...

    class AntwoordFout(Exception):
        ...

    class DataOphalenFout(Exception):
        ...

    class NaarJsonFout(Exception):
        ...

    def get_url(self, url):
        return url

    def get_headers(self):
        return {
            "user-agent": urllib3.util.SKIP_HEADER,
        }

    def naar_json(self, response):
        try:
            return response.json()
        except Exception:
            raise BasisService.NaarJsonFout(
                f"Json antwoord verwacht: url={response.url}, status code={response.status_code}, tekst={response.text}"
            )

    def do_request(
        self, url, method="get", data={}, params={}, raw_response=True, cache_timeout=0
    ) -> Response | dict:
        action: Request = getattr(requests, method)
        url = self.get_url(url)
        action_params: dict = {
            "url": url,
            "headers": self.get_headers(),
            "json": data,
            "params": params,
            "timeout": self._timeout,
        }

        if cache_timeout and method == "get":
            cache_key = f"{url}?{urlencode(params)}"
            response = cache.get(cache_key)
            if not response:
                response: Response = action(**action_params)
                if int(response.status_code) == 200:
                    cache.set(cache_key, response, cache_timeout)
        else:
            response: Response = action(**action_params)

        if raw_response:
            return response
        return self.naar_json(response)
