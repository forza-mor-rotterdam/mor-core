import json

import celery
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6

LOCK_EXPIRE = 5


class BaseTaskWithRetry(celery.Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY


@shared_task(bind=True, base=BaseTaskWithRetry)
def convert_aanvullende_informatie_to_aanvullende_vragen(self, signaal_ids):
    from apps.signalen.models import Signaal

    for signaal_id in signaal_ids:
        signaal = Signaal.objects.get(pk=signaal_id)
        try:
            aanvullende_informatie = signaal.aanvullende_informatie
            print(f"Aanvullende informatie: {aanvullende_informatie}")
            if aanvullende_informatie:
                lines = aanvullende_informatie.strip().split("\\n")
                print(f"Lines: {lines}")
                aanvullende_vragen = []
                question = None
                answers = []
                for line in lines:
                    if not line:
                        continue
                    if "?" in line:
                        if question:
                            aanvullende_vragen.append(
                                {"question": f"{question.strip()}?", "answers": answers}
                            )
                            answers = []
                        question, *temp_answers = line.split("?")
                        answers.extend(
                            [
                                ans.strip()
                                for ans in temp_answers
                                if ans and ans != "null"
                            ]
                        )
                    else:
                        answers.append(line)
                if question and answers:
                    print(f"Question: {question}")
                    aanvullende_vragen.append(
                        {"question": f"{question.strip()}?", "answers": answers}
                    )
                signaal.aanvullende_vragen = json.dumps(aanvullende_vragen)
                print(f"Aanvullende vragen end: {signaal.aanvullende_vragen}")
                signaal.save()
        except Exception as e:
            print(
                f"Error converting aanvullende_informatie to aanvullende_vragen for signaal {signaal.pk}: {e}"
            )
            logger.error(
                f"Error converting aanvullende_informatie to aanvullende_vragen for signaal {signaal.pk}: {e}"
            )
