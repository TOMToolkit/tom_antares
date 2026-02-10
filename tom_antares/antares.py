import logging
import json
from typing import List, Tuple, Dict

import antares_client
import marshmallow
from antares_client.search import get_available_tags, get_by_ztf_object_id, get_by_id
from astropy.time import Time, TimezoneInfo
from datetime import datetime, timezone
from crispy_forms.layout import HTML, Div, Fieldset, Layout
from django import forms

from tom_dataservices.dataservices import DataService
from tom_antares import __version__
from tom_alerts.alerts import GenericAlert, GenericBroker, GenericQueryForm
from tom_targets.models import Target, TargetName
from tom_dataproducts.models import ReducedDatum

from tom_antares.forms import AntaresForm

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
    surveys = {
        1: 'ZTF',
        2: 'ZTF',
        3: 'DECAT',
        4: 'LSST',
    }  # see antares_devkit.models.SURVEYS

    @classmethod
    def alert_to_dict(cls, locus):
        """
        Note: The ANTARES API returns a Locus object, which in the TOM Toolkit
        would otherwise be called an alert.

        This method serializes the Locus into a dict so that it can be cached by the view.
        """
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

    def process_reduced_data(self, target, alert=None):
        if alert is None:
            return

        for datum in alert['alerts']:
            value = {
                'limit': datum['properties']['ant_maglim'],
                'filter': datum['properties']['ant_passband'],
            }
            if 'ant_mag' in datum['properties']:
                value['magnitude'] = datum['properties']['ant_mag']
            if 'ant_magerr' in datum['properties']:
                value['error'] = datum['properties']['ant_magerr']
            ReducedDatum.objects.get_or_create(
                target=target,
                timestamp=Time(datum['properties']['ant_mjd'], format='mjd').to_datetime(timezone=TimezoneInfo()),
                data_type='photometry',
                source_name=f"{self.surveys[datum['properties']['ant_survey']]} (ANTARES)",
                value=value,
            )

    def to_target(self, alert: dict) -> Tuple[Target, Dict[str, str], List[str]]:
        """Create a target and aliases from an alert"""
        target = Target.objects.create(
            name=alert['locus_id'],
            type='SIDEREAL',
            ra=alert['ra'],
            dec=alert['dec'],
        )
        aliases = self.aliases_from_locus(alert, target)
        return target, {}, aliases

    def aliases_from_locus(self, alert, target):
        aliases = []
        if target.name != alert['locus_id']:
            aliases.append(TargetName(target=target, name=alert['locus_id']))
        if 'ztf' in alert['properties']['survey']:
            aliases += [
                TargetName(target=target, name=name)
                for name in alert['properties']['survey']['ztf']['id']
            ]
        if 'lsst' in alert['properties']['survey']:  #TODO: make sure this is how antares formats LSST alerts
            aliases += [
                TargetName(target=target, name=name)
                for name in alert['properties']['survey']['lsst']['dia_object_id']
            ]
        if alert['properties'].get(
            'horizons_targetname'
        ):
            aliases.append(
                TargetName(target=target, name=alert['properties'].get('horizons_targetname'))
            )
        return aliases

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


class AntaresDataService(DataService):
    """
        The ``AntaresDataService``
    """
    name = 'Antares'
    info_url = 'https://nsf-noirlab.gitlab.io/csdc/antares/client/tutorial/searching.html'
    app_version = __version__
    app_link = 'https://github.com/TOMToolkit/tom_antares'

    @classmethod
    def get_form_class(cls):
        return AntaresForm

    def get_simple_form_partial(self):
        """Returns a path to a simplified bare-minimum partial form that can be used to access the DataService."""
        return 'tom_antares/partials/antares_simple_form'

    def get_advanced_form_partial(self):
        """Returns a path to a simplified bare-minimum partial form that can be used to access the DataService."""
        return 'tom_antares/partials/antares_advanced_form'

    def build_query_parameters(self, parameters, **kwargs):
        data = {
            'ztfid': parameters.get('ztfid'),
            'antid': parameters.get('antid'),
            'elsquery': parameters.get('esquery'),
            'filters': []
        }

        # Filter on number of observations
        nobs_gt = parameters.get('nobs__gt')
        nobs_lt = parameters.get('nobs__lt')
        if nobs_gt or nobs_lt:
            nobs_range = {'range': {'properties.num_mag_values': {}}}
            if nobs_gt:
                nobs_range['range']['properties.num_mag_values']['gte'] = nobs_gt
            if nobs_lt:
                nobs_range['range']['properties.num_mag_values']['lte'] = nobs_lt
            data['filters'].append(nobs_range)

        # Filter data by date
        last_day = parameters.get('last_day')
        mjd_gt = parameters.get('mjd__gt')
        mjd_lt = parameters.get('mjd__lt')
        if last_day:
            # Set range to last 24 hours
            ut = Time(datetime.now(tz=timezone.utc), scale='utc')
            mjd_range = {
                'range': {
                    'properties.newest_alert_observation_time': {
                        'lte': ut.mjd,
                        'gte': ut.mjd - 1.0,
                    }
                }
            }
            data['filters'].append(mjd_range)
        else:
            if mjd_lt:
                # Set upper MJD time for alerts
                mjd_lt_range = {
                    'range': {
                        'properties.newest_alert_observation_time': {'lte': mjd_lt}
                    }
                }
                data['filters'].append(mjd_lt_range)
            if mjd_gt:
                # Set oldest MJD time for alerts
                mjd_gt_range = {
                    'range': {
                        'properties.oldest_alert_observation_time': {'gte': mjd_gt}
                    }
                }
                data['filters'].append(mjd_gt_range)

        # Filter on Magnitude
        mag_min = parameters.get('mag__min')
        mag_max = parameters.get('mag__max')
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
            data['filters'].append(mag_range)

        # Filter by Coordinates
        sra = parameters.get('ra')
        sdec = parameters.get('dec')
        ssr = parameters.get('sr')
        if sra and ssr:  # TODO: add cross-field validation
            ra_range = {'range': {'ra': {'gte': sra - ssr, 'lte': sra + ssr}}}
            data['filters'].append(ra_range)

        if sdec and ssr:  # TODO: add cross-field validation
            dec_range = {'range': {'dec': {'gte': sdec - ssr, 'lte': sdec + ssr}}}
            data['filters'].append(dec_range)

        # Filter on Tags
        tags = parameters.get('tag')
        if tags:
            data['filters'].append({'terms': {'tags': tags}})

        data['max_objects'] = parameters.get('max_alerts', 20)

        self.query_parameters = data
        return data

    def query_service(self, data, **kwargs):
        if data.get('ztfid'):
            self.query_results = get_by_ztf_object_id(data['ztfid'])
            return self.query_results
        elif data.get('antid'):
            self.query_results = get_by_id(data['antid'])
            return self.query_results
        elif data.get('elsquery'):
            self.query_results = antares_client.search.search(data['elsquery'])
            return self.query_results
        filter_query = {'query': {'bool': {'filter': data.get('filters', [])}}}
        self.query_results = antares_client.search.search(filter_query)
        return self.query_results

    def query_targets(self, data):
        loci = self.query_service(data)
        targets = []
        if loci:
            if isinstance(loci, antares_client.models.Locus):
                loci = [loci]
            for i, locus in enumerate(loci):
                result = {'name': locus.locus_id,
                          'ra': locus.ra,
                          'dec': locus.dec,
                          'mag': locus.properties.get('newest_alert_magnitude', ''),
                          'tags': locus.tags,
                          'aliases': self.query_aliases(data, locus=locus),
                          'reduced_datums': {'photometry': self.query_photometry(data, locus)}
                          }
                targets.append(result)
                if i+1 == data.get('max_objects', 20):
                    break
        self.target_results = targets
        return targets

    def query_aliases(self, query_parameters, locus=None, **kwargs):
        """Set up and run a specialized query for retrieving alternate names from a DataService."""
        if not locus:
            locus = self.query_results or self.query_service(query_parameters)
        aliases = []
        for id_key in ['ztf_object_id']:
            alias = locus.properties.get(id_key)
            if alias:
                aliases.append(alias)

        return aliases

    def query_photometry(self, query_parameters, locus=None, **kwargs):
        """Convert the lightcurve pandas dataframe into a list of dictionaries."""
        if not locus:
            locus = self.query_results or self.query_service(query_parameters)

        lightcurve = json.loads(locus.lightcurve.to_json(orient='records'))

        self.photometry_results[locus.locus_id] = lightcurve
        return lightcurve

    def create_target_from_query(self, target_result, **kwargs):
        """Create a new target from the query results
        :returns: target object
        :rtype: `Target`
        """

        target = Target(
            name=target_result['name'],
            type='SIDEREAL',
            ra=target_result['ra'],
            dec=target_result['dec']
        )
        return target

    def create_aliases_from_query(self, alias_results, **kwargs):
        """Create new TargetNames from the query results
        :returns: list of aliases to be added to a new Target
        :rtype: `list`
        """
        aliases = []
        for alias in alias_results:
            aliases.append(TargetName(name=alias))
        return aliases

    def create_reduced_datums_from_query(self, target, data=None, data_type='photometry', **kwargs):
        """Create and save new reduced_datums of the appropriate data_type from the query results"""

        reduced_datums = []
        for datum in data:
            datum_details = dict(datum)
            datum_details['magnitude'] = datum['ant_mag']
            datum_details['error'] = datum['ant_magerr']
            datum_details['limit'] = datum['ant_maglim']
            datum_details['filter'] = datum['ant_passband']

            reduced_datum, __ = ReducedDatum.objects.get_or_create(
                target=target,
                timestamp=Time(datum['time'], format='iso', scale='utc').to_datetime(timezone=TimezoneInfo()),
                data_type=data_type,
                source_name='Antares',
                value=datum_details
            )
            reduced_datums.append(reduced_datum)
        return reduced_datums
