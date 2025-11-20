from django import forms
from tom_dataservices.forms import BaseQueryForm


class AntaresForm(BaseQueryForm):
    target_name = forms.CharField(required=False,
                                  label='Target Name',
                                  help_text='Name')
