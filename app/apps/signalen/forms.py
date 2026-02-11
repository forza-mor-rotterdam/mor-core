from django import forms


class UpdateSignaalSignaalUrlForm(forms.Form):
    csv_file = forms.FileField()
    url_prefix = forms.CharField(required=False)
    dryrun = forms.BooleanField(initial=True, required=False)
    trailing_slash = forms.BooleanField(initial=False, required=False)
    raw_query = forms.BooleanField(initial=False, required=False)
    background_task = forms.BooleanField(initial=False, required=False)
