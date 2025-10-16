import logging

from apps.services.basis import BasisService

logger = logging.getLogger(__name__)


class OnderwerpenService(BasisService):
    def get_onderwerp(self, url) -> dict:
        return self.do_request(url, cache_timeout=120, raw_response=False)
