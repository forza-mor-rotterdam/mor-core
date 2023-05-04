from apps.meldingen.utils import get_q_objects_from_qs
from django.db.models import QuerySet


class SignaalQuerySet(QuerySet):
    def filter_to_get_melding(self, signaal_instance):
        try:
            ontdubbelregel = signaal_instance.bron.ontdubbelregel
        except Exception as e:
            print(e)
            return
        formatted_ontdubbelregel = signaal_instance.parse_querystring(ontdubbelregel)
        try:
            result = self.filter(
                get_q_objects_from_qs(formatted_ontdubbelregel), melding__isnull=False
            )
        except Exception as e:
            print(e)
            return
        if result:
            print("Maybe check to see if all of these Signalen share the same Melding")
            return result.first.melding
        return


class MeldingQuerySet(QuerySet):
    ...