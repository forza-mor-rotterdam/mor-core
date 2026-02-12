import json

import celery
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.utils import timezone

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


def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict.
    Assume the column names are unique.
    """
    if not cursor.description:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def set_signaal_url_by_given_id_bron_signaal_id(
    url_prefix,
    id_bron_signaal_id_list,
    bron_id,
    trailing_slash=False,
    dryrun=True,
    raw_query=False,
):
    from apps.signalen.models import Signaal

    prefix = url_prefix.strip("/")
    prefix = f"{prefix}/" if prefix else ""
    trailing_slash = "/" if trailing_slash else ""
    try:
        url_lookup = {
            id_bron_signaal_id[0]: id_bron_signaal_id[1]
            for id_bron_signaal_id in id_bron_signaal_id_list
        }
    except Exception as e:
        logger.error(f"set_signaal_url_by_given_id_bron_signaal_id: error={e}")

    id_list = [signaal[0] for signaal in id_bron_signaal_id_list]
    signalen_updated = []
    signalen = []

    if (raw_query and dryrun) or not raw_query:
        signalen = Signaal.objects.filter(bron_id=bron_id, bron_signaal_id__in=id_list)
        for signaal in signalen:
            bron_signaal_id = signaal.bron_signaal_id
            signaal_url = f"{prefix}{url_lookup[bron_signaal_id]}{trailing_slash}"
            signalen_updated.append([signaal.bron_signaal_id])
            signaal.signaal_url = signaal_url

    if not raw_query and not dryrun:
        Signaal.objects.bulk_update(signalen, ["signaal_url"])

    if raw_query and not dryrun:
        params = [
            sig_item
            for signaal in id_bron_signaal_id_list
            for sig_item in [
                signaal[0],
                bron_id,
                f"{prefix}{signaal[1]}{trailing_slash}",
            ]
        ]
        case_sql = " ".join(
            [
                'WHEN ("signalen_signaal"."bron_signaal_id" = %s AND "signalen_signaal"."bron_id" = %s) THEN %s'
                for _ in id_bron_signaal_id_list
            ]
        )
        params = params + [signaal[0] for signaal in id_bron_signaal_id_list]
        params = params + [bron_id]
        in_sql = ", ".join(["%s" for _ in id_bron_signaal_id_list])
        sql = f'UPDATE "signalen_signaal" \
            SET "signaal_url" = (CASE {case_sql} ELSE NULL END)::varchar(200) \
            WHERE "signalen_signaal"."bron_signaal_id" IN ({in_sql}) \
                AND "signalen_signaal"."bron_id" = %s \
            RETURNING "signalen_signaal"."bron_signaal_id"'

        with connections[settings.READONLY_DATABASE_KEY].cursor() as cursor:
            cursor.execute("SET statement_timeout TO 240000")
            cursor.execute(sql, params)
            signalen_updated = [
                list(signaal.values()) for signaal in dictfetchall(cursor)
            ]

    bron_signaal_id_not_found_list = [
        id for id in id_list if id not in [signaal[0] for signaal in signalen_updated]
    ]
    return {
        "source_bron_signaal_id_list": id_list,
        "bron_signaal_id_not_found_list": bron_signaal_id_not_found_list,
        "signalen_updated": signalen_updated,
    }


@shared_task(bind=True)
def task_set_signaal_url_by_given_id_bron_signaal_id(
    self,
    url_prefix,
    id_bron_signaal_id_list,
    bron_id,
    trailing_slash=False,
    dryrun=True,
    raw_query=False,
    background_task=False,
):
    cache_timeout = 60 * 60 * 24 * 14
    start = timezone.now()
    results = set_signaal_url_by_given_id_bron_signaal_id(
        url_prefix,
        id_bron_signaal_id_list,
        bron_id,
        trailing_slash=trailing_slash,
        dryrun=dryrun,
        raw_query=raw_query,
    )
    finish = timezone.now()

    cache.set(
        "signaal_url_update_summary",
        {
            "start_datetime": start.isoformat(),
            "finish_datetime": finish.isoformat(),
            "duration_ms": round((finish - start).microseconds / 1000),
            "source_bron_signaal_id_list_count": len(
                results["source_bron_signaal_id_list"]
            ),
            "signalen_updated_count": len(results["signalen_updated"]),
            "bron_signaal_id_not_found_list_count": len(
                results["bron_signaal_id_not_found_list"]
            ),
            "bron_id": bron_id,
            "url_prefix": url_prefix,
            "trailing_slash": trailing_slash,
            "dryrun": dryrun,
            "raw_query": raw_query,
            "background_task": background_task,
        },
        timeout=cache_timeout,
    )
    cache.set(
        "source_bron_signaal_id_list",
        results["source_bron_signaal_id_list"],
        timeout=cache_timeout,
    )
    cache.set(
        "signalen_updated",
        results["signalen_updated"],
        timeout=cache_timeout,
    )
    return {
        "source_bron_signaal_id_list_count": len(
            results["source_bron_signaal_id_list"]
        ),
        "signalen_updated_count": len(results["signalen_updated"]),
    }
