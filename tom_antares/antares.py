import json
import logging
from datetime import datetime, timezone

import antares_client
import numpy as np
from antares_client.search import get_available_tags, get_by_id, get_by_ztf_object_id
from astropy.time import Time, TimezoneInfo
from django.db import IntegrityError
from tom_dataproducts.models import PhotometryReducedDatum
from tom_dataservices.dataservices import DataService, QueryServiceError
from tom_targets.models import Target

from tom_antares import __version__
from tom_antares.forms import AntaresForm

logger = logging.getLogger(__name__)

ANTARES_BASE_URL = 'https://antares.noirlab.edu'


def get_tag_choices():
    tags = get_available_tags()
    return [(s, s) for s in tags]


def nan2str(obj):
    """
    Remove any NaN or Infinity from an object before JSON encoding
    """
    if isinstance(obj, dict):
        return {k: nan2str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [nan2str(v) for v in obj]
    elif isinstance(obj, float) and not np.isfinite(obj):
        return str(obj)
    return obj


class AntaresDataService(DataService):
    """
        The ``AntaresDataService``
    """
    name = 'Antares'
    info_url = 'https://nsf-noirlab.gitlab.io/csdc/antares/client/tutorial/searching.html'
    app_version = __version__
    app_link = 'https://github.com/TOMToolkit/tom_antares'
    surveys = {
        1: 'ZTF',
        2: 'ZTF',
        3: 'DECAT',
        4: 'LSST',
    }  # see antares_devkit.models.SURVEYS

    @classmethod
    def get_form_class(cls):
        return AntaresForm

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

    def build_query_parameters_from_target(self, target, **kwargs):
        """
        This is a method that builds query parameters based on an existing target object that will be recognized by
        `query_service()`.
        This can be done by either by re-creating the form fields set by the Data Service Form and then calling
        `self.build_query_parameters()` with the results, or we can reproduce a limited set of parameters uniquely for
        a target query.

        :param target: A target object to be queried
        :return: query_parameters (usually a dict) that can be understood by `query_service()`
        """

        for name in target.names:
            if name.startswith('ZTF'):
                parameters = {'ztfid': name}
                break
            elif target.name.startswith('ANT'):
                parameters = {'antid': name}
                break
        else:
            parameters = {'ra': target.ra, 'dec': target.dec, 'sr': 1. / 3600.}  # hardcoding 1 arcsec for now
        return self.build_query_parameters(parameters)

    def query_service(self, data, **kwargs):
        try:
            if data.get('ztfid'):
                self.query_results = [get_by_ztf_object_id(data['ztfid'])]
                return self.query_results
            elif data.get('antid'):
                self.query_results = [get_by_id(data['antid'])]
                return self.query_results
            elif data.get('elsquery'):
                self.query_results = antares_client.search.search(data['elsquery'])
                return self.query_results
            filter_query = {'query': {'bool': {'filter': data.get('filters', [])}}}
            self.query_results = antares_client.search.search(filter_query)
            return self.query_results
        except Exception as e:
            raise QueryServiceError(e)

    def serialize_locus(self, data, locus):
        result = {'name': locus.locus_id,
                  'ra': locus.ra,
                  'dec': locus.dec,
                  'mag': locus.properties.get('newest_alert_magnitude', ''),
                  'tags': locus.tags,
                  'aliases': self.query_aliases(data, locus=locus),
                  'reduced_datums': {'photometry': self.query_photometry(data, locus)}
                  }
        return nan2str(result)

    def query_targets(self, data):
        loci = self.query_service(data)
        targets = []
        for i, locus in enumerate(loci):
            result = self.serialize_locus(data, locus)
            targets.append(result)
            if i+1 == data.get('max_objects', 20):
                break
        self.target_results = targets
        return targets

    def query_aliases(self, query_parameters=None, target=None, locus=None, **kwargs):
        """Set up and run a specialized query for retrieving alternate names from a DataService."""
        if locus:
            loci = [locus]
        elif self.query_results:
            loci = self.query_results
        elif query_parameters:
            loci = self.query_service(query_parameters)
        elif target:
            loci = self.query_service(self.build_query_parameters_from_target(target))
        else:
            return []

        aliases = []
        for locus in loci:
            aliases.append(locus.locus_id)
            for id_key in ['ztf_object_id']:
                alias = locus.properties.get(id_key)
                if alias:
                    aliases.append(alias)
            break  # do not include aliases from more than one locus

        return aliases

    def query_photometry(self, query_parameters, locus=None, **kwargs):
        """Convert the lightcurve pandas dataframe into a list of dictionaries."""
        if locus:
            loci = [locus]
        else:
            loci = self.query_results or self.query_service(query_parameters)

        photometry = []
        for locus in loci:
            lightcurve = json.loads(locus.lightcurve.to_json(orient='records'))
            self.photometry_results[locus.locus_id] = lightcurve
            photometry += lightcurve
            break  # do not include photometry from more than one locus

        return photometry

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

    def create_reduced_datums_from_query(self, target, data, data_type='photometry', **kwargs):
        """Create and save new reduced_datums of the appropriate data_type from the query results"""

        reduced_datums = []
        for datum in data:
            datum_details = dict(datum)
            if (not (isinstance(datum['ant_mag'], float) and np.isfinite(datum['ant_mag']))
                    and not (isinstance(datum['ant_maglim'], float) and np.isfinite(datum['ant_maglim']))):
                continue
            if isinstance(datum['ant_mag'], float) and np.isfinite(datum['ant_mag']):
                datum_details['magnitude'] = datum['ant_mag']
            if isinstance(datum['ant_magerr'], float) and np.isfinite(datum['ant_magerr']):
                datum_details['error'] = datum['ant_magerr']
            if isinstance(datum['ant_maglim'], float) and np.isfinite(datum['ant_maglim']):
                datum_details['limit'] = datum['ant_maglim']
            datum_details['filter'] = datum['ant_passband']

            try:
                reduced_datum, _ = PhotometryReducedDatum.objects.get_or_create(
                    target=target,
                    timestamp=Time(
                        datum["time"], format="iso", scale="utc"
                    ).to_datetime(TimezoneInfo()),
                    source_name=f"{self.surveys[datum['ant_survey']]} ({self.name})",
                    brightness=datum_details.get("magnitude"),
                    brightness_error=datum_details.get("error"),
                    limit=datum_details.get("limit"),
                    bandpass=datum_details["filter"],
                )
            except IntegrityError:
                logger.warning(
                    (
                        "PhotometryReducedDatum already exists for target %s "
                        "with time %s and bandpass %s. Skipping."
                    ),
                    target.name,
                    datum["time"],
                    datum_details["filter"],
                )
                continue
            reduced_datums.append(reduced_datum)

        return reduced_datums
