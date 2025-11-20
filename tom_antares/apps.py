from django.apps import AppConfig


class TomAntaresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tom_antares'
    default = True

    def data_services(self):
        """
        integration point for including data services in the TOM
        This method should return a list of dictionaries containing dot separated DataService classes
        """
        return [{'class': f'{self.name}.antares.AntaresDataService'}]
