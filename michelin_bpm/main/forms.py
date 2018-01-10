# -*- coding: utf-8 -*-
from collections import OrderedDict

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext_lazy as l_

from .models import ProposalProcess


class FixMistakesForm(ModelForm):

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number'
        ]

    def __init__(self, *args, **kwargs):
        self.process_pk = kwargs.pop('process_pk')
        self.mistakes_from_step = kwargs.pop('mistakes_from_step', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        self.cleaned_data = super().clean()
        proposal = ProposalProcess.objects.get(pk=self.process_pk)
        corrections = proposal.get_corrected_fields(from_step=self.mistakes_from_step)

        for field_name, field in self.fields.items():
            correction_name = '{0}_correction'.format(field_name)
            if correction_name in corrections:
                # Проверяем, изменилось ли поле
                if getattr(proposal, field_name) == self.cleaned_data[field_name]:
                    self.add_error(field_name, l_('Нужно изменить требуемое поле'))
                    self.add_error(field_name, corrections[correction_name])

        if '__all__correction' in corrections:
            if not self.has_changed():
                self.add_error(None, l_('Нужно изменить хотя бы одно поле'))
                self.add_error(None, corrections['__all__correction'])

        return self.cleaned_data


class ApproveByAccountManagerForm(ModelForm):

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number', 'client'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        fields_with_corrections = OrderedDict()
        for field_name, field in self.fields.items():
            field.widget.attrs['readonly'] = True
            fields_with_corrections[field_name] = field
            fields_with_corrections['{}_correction'.format(field_name)] = forms.CharField(
                max_length=255,
                required=False
            )

        fields_with_corrections['__all__correction'] = forms.CharField(
                max_length=255,
                required=False,
                label=l_('Блокировка всей заявки без привязки к конкретному полю')
            )

        self.fields = fields_with_corrections
