from django import forms
from tom_dataservices.forms import BaseQueryForm
from antares_client.search import get_available_tags


def get_tag_choices():
    tags = get_available_tags()
    return [(s, s) for s in tags]


class AntaresForm(BaseQueryForm):
    # define form content
    ztfid = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(
            attrs={'placeholder': 'ZTF object id, e.g. ZTF19aapreis'}
        ),
    )
    antid = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(
            attrs={'placeholder': 'ANTARES locus id, e.g. ANT2020m4pja'}
        ),
    )
    tag = forms.MultipleChoiceField(required=False, choices=get_tag_choices)
    nobs__gt = forms.IntegerField(
        required=False,
        label='Detections Lower',
        widget=forms.TextInput(attrs={'placeholder': 'Min number of measurements'}),
    )
    nobs__lt = forms.IntegerField(
        required=False,
        label='Detections Upper',
        widget=forms.TextInput(attrs={'placeholder': 'Max number of measurements'}),
    )
    ra = forms.FloatField(
        required=False,
        label='RA',
        widget=forms.TextInput(attrs={'placeholder': 'RA (Degrees)'}),
        min_value=0.0,
        max_value=360.
    )
    dec = forms.FloatField(
        required=False,
        label='Dec',
        widget=forms.TextInput(attrs={'placeholder': 'Dec (Degrees)'}),
        min_value=0.0,
        max_value=90.,
    )
    sr = forms.FloatField(
        required=False,
        label='Search Radius',
        widget=forms.TextInput(attrs={'placeholder': 'radius (Degrees)'}),
        min_value=0.0,
    )
    mjd__gt = forms.FloatField(
        required=False,
        label='Min date of alert detection ',
        widget=forms.TextInput(attrs={'placeholder': 'Date (MJD)'}),
        min_value=0.0,
    )
    mjd__lt = forms.FloatField(
        required=False,
        label='Max date of alert detection',
        widget=forms.TextInput(attrs={'placeholder': 'Date (MJD)'}),
        min_value=0.0,
    )
    last_day = forms.BooleanField(
        required=False,
        label='Last 24hrs'
    )
    mag__min = forms.FloatField(
        required=False,
        label='Min magnitude of the latest alert',
        widget=forms.TextInput(attrs={'placeholder': 'Min Magnitude'}),
        min_value=0.0,
    )
    mag__max = forms.FloatField(
        required=False,
        label='Max magnitude of the latest alert',
        widget=forms.TextInput(attrs={'placeholder': 'Max Magnitude'}),
        min_value=0.0,
    )
    esquery = forms.JSONField(
        required=False,
        label='Elastic Search query in JSON format',
        widget=forms.Textarea(attrs={'placeholder': '{"query":{}}'}),
    )
    max_alerts = forms.IntegerField(
        label='Maximum number of alerts to fetch',
        widget=forms.TextInput(attrs={'placeholder': 'Max Alerts'}),
        min_value=1,
        initial=20,
    )

    def simple_fields(self):
        return ['antid']
