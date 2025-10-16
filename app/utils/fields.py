from django.contrib.gis.db import models


class DictJSONField(models.JSONField):
    empty_values = [None, "", [], ()]

    def formfield(self, **kwargs):
        result = super().formfield(**kwargs)
        result.empty_values = self.empty_values
        return result


class ListJSONField(models.JSONField):
    empty_values = [None, "", {}, ()]

    def formfield(self, **kwargs):
        result = super().formfield(**kwargs)
        result.empty_values = self.empty_values
        return result
