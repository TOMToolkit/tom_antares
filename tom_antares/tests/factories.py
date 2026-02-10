import factory

from antares_client.models import Alert, Locus
from pandas.core.frame import DataFrame


class AlertFactory(factory.Factory):
    """Creates a test version of an Alert object."""
    class Meta:
        model = Alert

    alert_id = factory.Faker('pystr')  # sample value: ztf_upper_limit:ZTF20achooum-1372493490015
    mjd = factory.Faker('pyfloat', min_value=58000, max_value=63000)  # sample value: 59126.493495400064
    properties = factory.Dict({
         'ztf_jd': factory.Faker('pyfloat', min_value=2458000, max_value=2463000),  # sample value: 2459126.9934954,
         'ztf_fid': factory.Faker('pyint', min_value=1, max_value=3),  # sample value: 1,
         # ztf_pid sample value: 1372493490015
         'ztf_pid': factory.Faker('pyint', min_value=1000000000000, max_value=9999999999999),
         'ztf_diffmaglim': factory.Faker('pyfloat', min_value=15, max_value=23),  # sample value: 19.29050064086914,
         # NOTE: the remaining properties are unused by our code
         # 'ztf_pdiffimfilename':
         # sample: '/ztf/archive/sci/2020/1004/493495/ztf_20201004493495_000817_zg_c01_o_q1_scimrefdiffimg.fits.fz',
         # 'ztf_programpi':  # sample value: 'Kulkarni',
         # 'ztf_programid':  # sample value: 1,
         # 'ztf_nid':  # sample value: 1372,
         # 'ztf_rcid':  # sample value: 0,
         # 'ztf_field':  # sample value: 817,
         # 'ztf_magzpsci':  # sample value: 26.03019905090332,
         # 'ztf_magzpsciunc':  # sample value: 2.967269938380923e-05,
         # 'ztf_magzpscirms':  # sample value: 0.03643900156021118,
         # 'ztf_clrcoeff':  # sample value: -0.04269000142812729,
         # 'ztf_clrcounc':  # sample value: 5.5116099247243255e-05,
         # 'ztf_rbversion':  # sample value: 't17_f5_c3',
         # 'ant_mjd':  # sample value: 59126.493495400064,
         # 'ant_time_received':  # sample value: 1602073185,
         # 'ant_input_msg_time':  # sample value: 1602073179,
         # 'ant_passband':  # sample value: 'g',
         # 'ant_maglim':  # sample value: 19.29050064086914,
         # 'ant_survey':  # sample value: 2
    })


lightcurve_data = [{"time": "2019-04-01 11:39:44.999992",
                    "alert_id": "ztf_upper_limit:ZTF19aapreis-820485935515",
                    "ant_mjd": 58574.4859374999,
                    "ant_survey": 2,
                    "ant_ra": None,
                    "ant_dec": None,
                    "ant_passband": "R",
                    "ant_mag": None,
                    "ant_magerr": None,
                    "ant_maglim": 17.7894001007,
                    "ant_mag_corrected": None,
                    "ant_magerr_corrected": None
                    },

                   {"time": "2019-04-20 10:42:10.995834",
                    "alert_id": "ztf_candidate:839445965515015001",
                    "ant_mjd": 58593.4459605999,
                    "ant_survey": 1,
                    "ant_ra": 314.2624159,
                    "ant_dec": 14.2045147,
                    "ant_passband": "R",
                    "ant_mag": 18.2996997833,
                    "ant_magerr": 0.0943880007,
                    "ant_maglim": 19.2355995178,
                    "ant_mag_corrected": None,
                    "ant_magerr_corrected": None
                    }
                   ]


class LocusFactory(factory.Factory):
    """Creates a test version of a Locus object

    Requires a list of alerts as a kwarg

    Example Locus:

    locus = Locus(locus_id='ANT2020aeczfyy', ra=159.6231717, dec=59.839694,
                  properties={'ztf_object_id': 'ZTF20achooum',
                          'ztf_ssnamenr': 'null',
                          'num_alerts': 3,
                          'num_mag_values': 1,
                          'oldest_alert_id': 'ztf_candidate:1375506740015015002',
                          'oldest_alert_magnitude': 18.615400314331055,
                          'oldest_alert_observation_time': 59129.50674769981,
                          'newest_alert_id': 'ztf_candidate:1375506740015015002',
                          'newest_alert_magnitude': 18.615400314331055,
                          'newest_alert_observation_time': 59129.50674769981,
                          'brightest_alert_id': 'ztf_candidate:1375506740015015002',
                          'brightest_alert_magnitude': 18.615400314331055,
                          'brightest_alert_observation_time': 59129.50674769981},
                  tags=['in_m31'],
                  alerts=[
                    Alert(alert_id='ztf_upper_limit:ZTF20achooum-1372493490015',
                          mjd=59126.493495400064,
                          properties={},)
                  ]
                )
    """
    class Meta:
        model = Locus

    @classmethod
    def create(cls, **kwargs):
        if not kwargs.get('alerts'):
            alerts = [AlertFactory.create() for i in range(0, 5)]
            kwargs.update({'alerts': alerts})
        return super().create(**kwargs)

    locus_id = factory.Faker('pystr')  # sample value: 'ANT2020aeczfyy'
    ra = factory.Faker('pyfloat')  # sample value: 159.6231717
    dec = factory.Faker('pyfloat')  # sample value: 59.839694
    properties = factory.Dict({
        'ztf_object_id': factory.Faker('pystr')  # sample value: 'ZTF20achooum',
        # NOTE: the remaining properties are unused by our code
        # 'ztf_ssnamenr':  # sample value: 'null',
        # 'num_alerts':  # sample value: 3,
        # 'num_mag_values':  # sample value: 1,
        # 'oldest_alert_id':  # sample value: 'ztf_candidate:1375506740015015002',
        # 'oldest_alert_magnitude':  # sample value: 18.615400314331055,
        # 'oldest_alert_observation_time':  # sample value: 59129.50674769981,
        # 'newest_alert_id':  # sample value: 'ztf_candidate:1375506740015015002',
        # 'newest_alert_magnitude':  # sample value: 18.615400314331055,
        # 'newest_alert_observation_time':  # sample value: 59129.50674769981,
        # 'brightest_alert_id':  # sample value: 'ztf_candidate:1375506740015015002',
        # 'brightest_alert_magnitude':  # sample value: 18.615400314331055,
        # 'brightest_alert_observation_time':  # sample value: 59129.50674769981
    })
    tags = factory.List([])
    lightcurve = DataFrame(lightcurve_data)
    catalogs = factory.List([])
    # catalog_objects = factory.List([])
    # watch_list_ids = factory.List([])
