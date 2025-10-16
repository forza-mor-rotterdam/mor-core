import uuid

from django.contrib.gis.db import models
from django.db.models.expressions import Func


class BasisModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    aangemaakt_op = models.DateTimeField(editable=False, auto_now_add=True)
    aangepast_op = models.DateTimeField(editable=False, auto_now=True)

    class Meta:
        abstract = True


class Epoch(Func):
    template = "EXTRACT(epoch FROM %(expressions)s)::DOUBLE PRECISION"
    output_field = models.FloatField()
