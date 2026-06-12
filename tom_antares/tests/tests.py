from django.test import TestCase
from unittest import mock

from tom_antares.antares import AntaresDataService
from tom_antares.tests.factories import LocusFactory, lightcurve_data
from tom_targets.models import Target, TargetName


class TestAntaresDataservice(TestCase):
    """
    Test the functionality of the Antares Dataservice
    NOTE: to run these tests in your venv: python ./tom_antares/tests/run_tests.py
    """

    def setUp(self):
        self.test_target = Target.objects.create(name='ZTF20achooum')
        self.antares_query = AntaresDataService()
        self.loci = [LocusFactory.create() for i in range(0, 5)]
        self.locus = self.loci[0]
        self.locus_id = 'ANT2025v5k9wxb6vzbe'
        self.tag = 'in_m31'

    def test_build_query_parameters(self):
        """
        Test that we properly construct filters for antares query.
        """
        form_parameters = {'query_save': True,
                           'query_name': 'a mess',
                           'data_service': 'Antares',
                           'ztfid': 'ZTF_name',
                           'antid': 'Ant_name',
                           'tag': ['lc_feature_extractor', 'sso_candidates'],
                           'nobs__gt': 10,
                           'nobs__lt': 100,
                           'ra': 12.0,
                           'dec': 12.0,
                           'sr': 12.0,
                           'mjd__gt': 61000.0,
                           'mjd__lt': 61005.0,
                           'last_day': False,
                           'mag__min': 2.0,
                           'mag__max': 10.0,
                           'esquery': None,
                           'max_alerts': 20
                           }
        expected_query_parameters = {'ztfid': 'ZTF_name',
                                     'antid': 'Ant_name',
                                     'elsquery': None,
                                     'filters': [{'range': {'properties.num_mag_values': {'gte': 10, 'lte': 100}}},
                                                 {'range': {'properties.newest_alert_observation_time':
                                                            {'lte': 61005.0}}
                                                  },
                                                 {'range': {'properties.oldest_alert_observation_time':
                                                            {'gte': 61000.0}}
                                                  },
                                                 {'range': {'properties.newest_alert_magnitude':
                                                            {'gte': 2.0, 'lte': 10.0}
                                                            }
                                                  },
                                                 {'range': {'ra': {'gte': 0.0, 'lte': 24.0}}},
                                                 {'range': {'dec': {'gte': 0.0, 'lte': 24.0}}},
                                                 {'terms': {'tags': ['lc_feature_extractor', 'sso_candidates']}}
                                                 ],
                                     'max_objects': 20
                                     }
        query_parameters = self.antares_query.build_query_parameters(form_parameters)
        self.assertEqual(query_parameters, expected_query_parameters)

    @mock.patch('tom_antares.antares.get_by_id')
    def test_query_targets_single(self, mock_client):
        mock_client.side_effect = [self.locus]
        targets = self.antares_query.query_targets({'antid': 'Ant_name'})
        expected_target_results = {'name': self.locus.locus_id,
                                   'ra': self.locus.ra,
                                   'dec': self.locus.dec,
                                   'mag': '',
                                   'tags': [],
                                   'aliases': [self.locus.locus_id, self.locus.properties.get('ztf_object_id')],
                                   'reduced_datums': {'photometry': lightcurve_data}}
        for target in targets:
            for key in target.keys():
                self.assertEqual(target[key], expected_target_results[key])

    @mock.patch('antares_client.search.search')
    def test_query_targets_many(self, mock_client):
        mock_client.side_effect = lambda loci: iter(self.loci)
        targets = self.antares_query.query_targets({'max_objects': 4})
        self.assertEqual(len(targets), 4)

    @mock.patch('tom_antares.antares.get_by_id')
    def test_query_aliases(self, mock_client):
        mock_client.side_effect = [self.locus]
        aliases = self.antares_query.query_aliases(query_parameters={'antid': 'Ant_name'})
        self.assertEqual(aliases, [self.locus.locus_id, self.locus.properties.get('ztf_object_id')])

    @mock.patch('tom_antares.antares.get_by_id')
    def test_query_photometry(self, mock_client):
        mock_client.side_effect = [self.locus]
        phot_data = self.antares_query.query_photometry({'antid': 'Ant_name'}, self.locus)
        expected_phot = lightcurve_data
        self.assertEqual(phot_data, expected_phot)

    def test_create_target_from_query(self):
        target_results = {'name': self.locus.locus_id,
                          'ra': self.locus.ra,
                          'dec': self.locus.dec,
                          'mag': '',
                          'tags': [],
                          'aliases': [self.locus.properties.get('ztf_object_id')],
                          'reduced_datums': {'photometry': lightcurve_data}}
        target = self.antares_query.create_target_from_query(target_results)
        self.assertIsInstance(target, Target)

    def test_create_aliases_from_query(self):
        aliases_results = ['ztf_name', 'other_name']
        aliases = self.antares_query.create_aliases_from_query(aliases_results)
        for alias in aliases:
            self.assertIsInstance(alias, TargetName)

    def test_create_reduced_datums_from_query(self):
        reduced_data = self.antares_query.create_reduced_datums_from_query(self.test_target, lightcurve_data)
        keys_list = [('ant_mag', 'brightness'),
                     ('ant_magerr', 'brightness_error'),
                     ('ant_maglim', 'limit'),
                     ('ant_passband', 'bandpass')]
        for i, reduced_datum in enumerate(reduced_data):
            for key in keys_list:
                if lightcurve_data[i][key[0]]:
                    self.assertEqual(getattr(reduced_datum, key[1]), lightcurve_data[i][key[0]])
                else:
                    self.assertIsNone(getattr(reduced_datum, key[1]))
