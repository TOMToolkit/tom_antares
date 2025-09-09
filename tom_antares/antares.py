import logging

import antares_client
import marshmallow
from antares_client.search import get_available_tags, get_by_ztf_object_id, get_by_id
from astropy.time import Time, TimezoneInfo
from datetime import datetime, timezone
from crispy_forms.layout import HTML, Div, Fieldset, Layout
from django import forms
from tom_alerts.alerts import GenericAlert, GenericBroker, GenericQueryForm
from tom_targets.models import Target, TargetName

logger = logging.getLogger(__name__)

ANTARES_BASE_URL = 'https://antares.noirlab.edu'


def get_tag_choices():
    tags = get_available_tags()
    return [(s, s) for s in tags]


# class ConeSearchWidget(forms.widgets.MultiWidget):

#     def __init__(self, attrs=None):
#         if not attrs:
#             attrs = {}
#         _default_attrs = {'class': 'form-control col-md-4', 'style': 'display: inline-block'}
#         attrs.update(_default_attrs)
#         print(attrs)
#         ra_attrs.update({'placeholder': 'Right Ascension'})
#         print(ra_attrs)

#         _widgets = (
#             forms.widgets.NumberInput(attrs=ra_attrs),
#             forms.widgets.NumberInput(attrs=attrs.update({'placeholder': 'Declination'})),
#             forms.widgets.NumberInput(attrs=attrs.update({'placeholder': 'Radius (degrees)'}))
#         )

#         super().__init__(_widgets, attrs)

#     def decompress(self, value):
#         return [value.ra, value.dec, value.radius] if value else [None, None, None]


# class ConeSearchField(forms.MultiValueField):
#     widget = ConeSearchWidget

#     def __init__(self, *args, **kwargs):
#         fields = (forms.FloatField(), forms.FloatField(), forms.FloatField())
#         super().__init__(fields=fields, *args, **kwargs)

#     def compress(self, data_list):
#         return data_list


class ANTARESBrokerForm(GenericQueryForm):
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
    )
    dec = forms.FloatField(
        required=False,
        label='Dec',
        widget=forms.TextInput(attrs={'placeholder': 'Dec (Degrees)'}),
        min_value=0.0,
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
    max_alerts = forms.FloatField(
        label='Maximum number of alerts to fetch',
        widget=forms.TextInput(attrs={'placeholder': 'Max Alerts'}),
        min_value=1,
        initial=20,
    )

    # cone_search = ConeSearchField()
    # api_search_tags = forms.MultipleChoiceField(choices=get_tag_choices)

    # TODO: add section for searching API in addition to consuming stream

    # TODO: add layout
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            self.common_layout,
            HTML(
                '''
                <p>
                Users can query objects in the ANTARES database using one of the following
                three methods: 1. an object ID by ZTF, 2. a simple query form with constraints
                of object brightness, position, and associated tag, 3. an advanced query with
                Elastic Search syntax.
            </p>
            '''
            ),
            HTML('<hr/>'),
            HTML('<h3>Query by object name</h3>'),
            Fieldset(
                'Object ID',
                Div(
                    Div(
                        'ztfid',
                        css_class='col',
                    ),
                    Div(
                        'antid',
                        css_class='col'
                    ),
                    css_class='form-row',
                )
            ),
            HTML('<hr/>'),
            HTML('<h3>Simple query form</h3>'),
            Fieldset(
                'Alert timing',
                Div(
                    Div(
                        'mjd__gt',
                        css_class='col',
                    ),
                    Div(
                        'mjd__lt',
                        css_class='col',
                    ),
                    Div(
                        'last_day',
                        css_class='col',
                    ),
                    css_class='form-row',
                ),
            ),
            Fieldset(
                'Number of measurements',
                Div(
                    Div(
                        'nobs__gt',
                        css_class='col',
                    ),
                    Div(
                        'nobs__lt',
                        css_class='col',
                    ),
                    css_class='form-row',
                ),
            ),
            Fieldset(
                'Brightness of the latest alert',
                Div(
                    Div(
                        'mag__min',
                        css_class='col',
                    ),
                    Div(
                        'mag__max',
                        css_class='col',
                    ),
                    css_class='form-row',
                ),
            ),
            Fieldset(
                'Cone Search',
                Div(
                    Div('ra', css_class='col'),
                    Div('dec', css_class='col'),
                    Div('sr', css_class='col'),
                    css_class='form-row',
                ),
            ),
            Fieldset('View Tags', 'tag'),
            Fieldset('Max Alerts', 'max_alerts'),
            HTML('<hr/>'),
            HTML('<h3>Advanced query</h3>'),
            Fieldset('', 'esquery'),
            HTML(
                '''
                <p>
                Please see <a href='https://nsf-noirlab.gitlab.io/csdc/antares/client/tutorial/searching.html'>ANTARES
                 Documentation</a> for a detailed description of advanced searches.
                </p>
            '''
            )
            # HTML('<hr/>'),
            # Fieldset(
            #     'API Search',
            #     'api_search_tags'
            # )
        )

    def clean(self):
        cleaned_data = super().clean()

        # Ensure all cone search fields are present
        if (
            any(cleaned_data[k] for k in ['ra', 'dec', 'sr'])
            and not all(cleaned_data[k] for k in ['ra', 'dec', 'sr'])
        ):
            raise forms.ValidationError(
                'All of RA, Dec, and Search Radius must be included to perform a cone search.'
            )
        # default value for cone search
        if not all(cleaned_data[k] for k in ['ra', 'dec', 'sr']):
            cleaned_data['ra'] = 180.0
            cleaned_data['dec'] = 0.0
            cleaned_data['sr'] = 180.0
        # Ensure alert timing constraints have sensible values
        if (
            all(cleaned_data[k] for k in ['mjd__lt', 'mjd__gt'])
            and cleaned_data['mjd__lt'] <= cleaned_data['mjd__gt']
        ):
            raise forms.ValidationError(
                'Min date of alert detection must be earlier than max date of alert detection.'
            )

        # Ensure number of measurement constraints have sensible values
        if (
            all(cleaned_data[k] for k in ['nobs__lt', 'nobs__gt'])
            and cleaned_data['nobs__lt'] <= cleaned_data['nobs__gt']
        ):
            raise forms.ValidationError(
                'Min number of measurements must be smaller than max number of measurements.'
            )

        # Ensure magnitude constraints have sensible values
        if (
            all(cleaned_data[k] for k in ['mag__min', 'mag__max'])
            and cleaned_data['mag__max'] <= cleaned_data['mag__min']
        ):
            raise forms.ValidationError(
                'Min magnitude must be smaller than max magnitude.'
            )

        # Ensure using either a stream or the advanced search form
        # if not (cleaned_data['tag'] or cleaned_data['esquery']):
        #    raise forms.ValidationError('Please either select tag(s) or use the advanced search query.')

        # Ensure using either a stream or the advanced search form
        if not (
            cleaned_data.get('ztfid')
            or cleaned_data.get('antid')
            or cleaned_data.get('tag')
            or cleaned_data.get('esquery')
            or (
                cleaned_data.get('mjd_lt')
                and cleaned_data.get('mjd_gt')
            )
            or cleaned_data.get('last_day')
        ):
            raise forms.ValidationError(
                'Please either enter an ID, date range, select tag(s), or use the advanced search query.'
            )

        return cleaned_data


class ANTARESBroker(GenericBroker):
    name = 'ANTARES'
    form = ANTARESBrokerForm

    @classmethod
    def alert_to_dict(cls, locus):
        '''
        Note: The ANTARES API returns a Locus object, which in the TOM Toolkit
        would otherwise be called an alert.

        This method serializes the Locus into a dict so that it can be cached by the view.
        '''
        return {
            'locus_id': locus.locus_id,
            'ra': locus.ra,
            'dec': locus.dec,
            'properties': locus.properties,
            'tags': locus.tags,
            # 'lightcurve': locus.lightcurve.to_json(),
            'catalogs': locus.catalogs,
            'alerts': [
                {
                    'alert_id': alert.alert_id,
                    'mjd': alert.mjd,
                    'properties': alert.properties,
                }
                for alert in locus.alerts
            ],
        }

    def fetch_alerts(self, parameters: dict) -> iter:
        tags = parameters.get('tag')
        nobs_gt = parameters.get('nobs__gt')
        nobs_lt = parameters.get('nobs__lt')
        sra = parameters.get('ra')
        sdec = parameters.get('dec')
        ssr = parameters.get('sr')
        mjd_gt = parameters.get('mjd__gt')
        mjd_lt = parameters.get('mjd__lt')
        last_day = parameters.get('last_day')
        mag_min = parameters.get('mag__min')
        mag_max = parameters.get('mag__max')
        elsquery = parameters.get('esquery')
        ztfid = parameters.get('ztfid')
        antid = parameters.get('antid')
        max_alerts = parameters.get('max_alerts', 20)
        alerts = []
        if antid:
            try:
                locus = get_by_id(antid)
            except antares_client.exceptions.AntaresException:
                locus = None
            if locus:
                alerts.append(self.alert_to_dict(locus))
        else:
            if ztfid:
                query = {
                    'query': {
                        'bool': {'must': [{'match': {'properties.ztf_object_id': ztfid}}]}
                    }
                }
            elif elsquery:
                query = elsquery
            else:
                filters = []

                if nobs_gt or nobs_lt:
                    nobs_range = {'range': {'properties.num_mag_values': {}}}
                    if nobs_gt:
                        nobs_range['range']['properties.num_mag_values']['gte'] = nobs_gt
                    if nobs_lt:
                        nobs_range['range']['properties.num_mag_values']['lte'] = nobs_lt
                    filters.append(nobs_range)

                if last_day:
                    ut = Time(datetime.now(tz=timezone.utc), scale='utc')
                    mjd_range = {
                        'range': {
                            'properties.newest_alert_observation_time': {
                                'lte': ut.mjd,
                                'gte': ut.mjd - 1.0,
                            }
                        }
                    }
                    filters.append(mjd_range)
                    mjd_lt = ''
                    mjd_gt = ''

                if mjd_lt:
                    mjd_lt_range = {
                        'range': {
                            'properties.newest_alert_observation_time': {'lte': mjd_lt}
                        }
                    }
                    filters.append(mjd_lt_range)

                if mjd_gt:
                    mjd_gt_range = {
                        'range': {
                            'properties.oldest_alert_observation_time': {'gte': mjd_gt}
                        }
                    }
                    filters.append(mjd_gt_range)

                if mag_min or mag_max:
                    mag_range = {'range': {'properties.newest_alert_magnitude': {}}}
                    if mag_min:
                        mag_range['range']['properties.newest_alert_magnitude'][
                            'gte'
                        ] = mag_min
                    if mag_max:
                        mag_range['range']['properties.newest_alert_magnitude'][
                            'lte'
                        ] = mag_max
                    filters.append(mag_range)

                if sra and ssr:  # TODO: add cross-field validation
                    ra_range = {'range': {'ra': {'gte': sra - ssr, 'lte': sra + ssr}}}
                    filters.append(ra_range)

                if sdec and ssr:  # TODO: add cross-field validation
                    dec_range = {'range': {'dec': {'gte': sdec - ssr, 'lte': sdec + ssr}}}
                    filters.append(dec_range)

                if tags:
                    filters.append({'terms': {'tags': tags}})

                query = {'query': {'bool': {'filter': filters}}}
            loci = antares_client.search.search(query)
            while len(alerts) < max_alerts:
                try:
                    locus = next(loci)
                except (marshmallow.exceptions.ValidationError, StopIteration):
                    break
                alerts.append(self.alert_to_dict(locus))
        return iter(alerts)

    def fetch_alert(self, id_):
        alert = get_by_ztf_object_id(id_)
        return alert

    def fetch_locus(self, id_):
        alert = get_by_id(id_)
        return alert

    # TODO: This function
    def process_reduced_data(self, target, alert=None):
        pass

    def to_target(self, alert: dict) -> Target:
        target = Target.objects.create(
            name=alert['properties']['ztf_object_id'],
            type='SIDEREAL',
            ra=alert['ra'],
            dec=alert['dec'],
        )
        antares_name = TargetName(target=target, name=alert['locus_id'])
        aliases = [antares_name]
        if alert['properties'].get(
            'horizons_targetname'
        ):  # TODO: review if any other target names need to be created
            aliases.append(
                TargetName(name=alert['properties'].get('horizons_targetname'))
            )
        return target, [], aliases

    def to_generic_alert(self, alert):
        url = f'{ANTARES_BASE_URL}/loci/{alert["locus_id"]}'
        timestamp = Time(
            alert['properties'].get('newest_alert_observation_time'),
            format='mjd',
            scale='utc',
        ).to_datetime(timezone=TimezoneInfo())
        return GenericAlert(
            timestamp=timestamp,
            url=url,
            id=alert['locus_id'],
            name=alert['properties']['ztf_object_id'],
            ra=alert['ra'],
            dec=alert['dec'],
            mag=alert['properties'].get('newest_alert_magnitude', ''),
            score=alert['alerts'][-1]['properties'].get('ztf_rb', ''),
        )
