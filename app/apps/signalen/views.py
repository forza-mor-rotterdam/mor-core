import csv
import logging

from apps.signalen.forms import UpdateSignaalSignaalUrlForm
from apps.signalen.models import Signaal
from apps.signalen.tasks import task_set_signaal_url_by_given_id_bron_signaal_id
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.encoding import smart_str
from django.views.generic import FormView, TemplateView, View

logger = logging.getLogger(__name__)


class UpdateSignaalSignaalUrlView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "update_signaal_signaal_url.html"
    form_class = UpdateSignaalSignaalUrlForm

    def test_func(self):
        return self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs):
        self.signaal_url_update_results = cache.get("signaal_url_update_results", [])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "signaal_url_update_results": self.signaal_url_update_results,
            }
        )
        return context

    def form_invalid(self, form):
        logger.error("UpdateSignaalSignaalUrlView: FORM INVALID")
        logger.error(form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        file = form.cleaned_data["csv_file"].read().decode("utf-8")
        data = []
        try:
            data = [
                line.split(";")
                for line in file.split("\n")
                if len(line.split(";")) == 2
            ]
        except Exception as e:
            logger.error(e)

        kwargs = {
            "url_prefix": form.cleaned_data["url_prefix"],
            "id_bron_signaal_id_list": data,
            "dryrun": form.cleaned_data["dryrun"],
            "trailing_slash": form.cleaned_data["trailing_slash"],
            "raw_query": form.cleaned_data["raw_query"],
            "background_task": form.cleaned_data["background_task"],
        }

        if form.cleaned_data["background_task"]:
            task_set_signaal_url_by_given_id_bron_signaal_id.delay(**kwargs)
        else:
            task_set_signaal_url_by_given_id_bron_signaal_id(**kwargs)

        context = {
            "signaal_url_update_results": self.signaal_url_update_results,
            "form": form,
        }

        response = render(
            self.request,
            self.template_name,
            context=context,
        )
        return response


class UpdateSignaalSignaalUrlSummaryView(
    LoginRequiredMixin, UserPassesTestMixin, TemplateView
):
    template_name = "update_signaal_signaal_url_result.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        signaal_url_update_summary = cache.get(
            "signaal_url_update_summary",
            {},
        )
        context.update(
            {
                "signaal_url_update_summary": signaal_url_update_summary,
            }
        )
        return context


class UpdateSignaalSignaalUrlResultView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        SIGNALEN_UPDATED_KEY = "signalen_updated"
        BRON_SIGNAAL_ID_NOT_FOUND_LIST_KEY = "bron_signaal_id_not_found_list"
        SOURCE_BRON_SIGNAAL_ID_LIST_KEY = "source_bron_signaal_id_list"
        SIGNALEN_AFGEHANDELD_LIST_KEY = "signalen_afgehandeld_list"
        SIGNALEN_OPENSTAAND_WRONG_SIGNAAL_URL_LIST_KEY = (
            "signalen_openstaand_wrong_signaal_url_list"
        )
        result_type = self.kwargs.get("result_type")
        if result_type not in [
            SOURCE_BRON_SIGNAAL_ID_LIST_KEY,
            BRON_SIGNAAL_ID_NOT_FOUND_LIST_KEY,
            SIGNALEN_UPDATED_KEY,
            SIGNALEN_AFGEHANDELD_LIST_KEY,
            SIGNALEN_OPENSTAAND_WRONG_SIGNAAL_URL_LIST_KEY,
        ]:
            raise Http404
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={result_type}.csv"
        writer = csv.writer(response, csv.excel)
        response.write("\ufeff".encode("utf8"))

        if result_type == BRON_SIGNAAL_ID_NOT_FOUND_LIST_KEY:
            signalen_updated = cache.get(SIGNALEN_UPDATED_KEY, [])
            source_bron_signaal_id_list = cache.get(SOURCE_BRON_SIGNAAL_ID_LIST_KEY, [])
            data = [
                id
                for id in source_bron_signaal_id_list
                if id not in [signaal[0] for signaal in signalen_updated]
            ]
        elif result_type == SIGNALEN_AFGEHANDELD_LIST_KEY:
            signalen_updated_id_list = [
                signaal[0] for signaal in cache.get(SIGNALEN_UPDATED_KEY, [])
            ]
            data = list(
                Signaal.objects.select_related("melding")
                .filter(
                    bron_signaal_id__in=signalen_updated_id_list,
                    melding__afgesloten_op__isnull=False,
                )
                .values_list("bron_signaal_id", flat=True)
            )
        elif result_type == SIGNALEN_OPENSTAAND_WRONG_SIGNAAL_URL_LIST_KEY:
            data = list(
                Signaal.objects.select_related("melding")
                .filter(
                    signaal_url__startswith="https://meldr.rotterdam.nl/melding/",
                    melding__afgesloten_op__isnull=True,
                )
                .values_list("bron_signaal_id", flat=True)
            )
        else:
            data = cache.get(result_type, [])
        for result_row in data:
            writer.writerow(
                [smart_str(item) for item in result_row]
                if isinstance(result_row, list)
                else [result_row]
            )
        return response
