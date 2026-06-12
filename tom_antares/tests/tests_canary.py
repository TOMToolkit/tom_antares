from django.test import tag, TestCase

from tom_antares.antares import AntaresDataService


@tag('canary')
class TestANTARESModuleCanary(TestCase):
    """NOTE: To run these tests in your venv: python ./tom_scimma/tests/run_tests.py"""

    def setUp(self):
        self.broker = AntaresDataService()

    def test_boilerplate(self):
        self.assertTrue(True)
