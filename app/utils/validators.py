import re

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


class URLTrailingSlashValidator(URLValidator):
    def __call__(self, value):
        super().__call__(value)
        trailing_slash_match = re.search(
            r"^(?![/]$|[/?].*$)(.*\/[?](.*)$|.*\/$)", value
        )

        if not trailing_slash_match:
            raise ValidationError(
                "De slash aan het eind van deze url is verplicht!",
                code=self.code,
                params={"value": value},
            )
