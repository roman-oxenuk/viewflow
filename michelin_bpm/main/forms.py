# -*- coding: utf-8 -*-
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext_lazy as l_

from reversion.models import Version
from viewflow.fields import get_task_ref

from michelin_bpm.main.models import Correction, ProposalProcess


CORR_SUFFIX = settings.CORRECTION_FIELD_SUFFIX


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

        # Проверяем, изменились ли те поля, к которым были указаны корректировки
        correction_obj = self.instance.get_correction_active(for_step=self.mistakes_from_step)
        need_to_be_corrected = set(correction_obj.data.keys())

        last_version = self.instance.get_last_version(for_step=self.mistakes_from_step)
        changed_fields = set(
            self.instance.get_diff_fields(
                self.cleaned_data, last_version, self.fields.keys()
            ).keys()
        )

        if '__all__' in need_to_be_corrected:
            if not changed_fields:
                self.add_error(None, l_('Нужно изменить хотя бы одно поле'))
                self.add_error(None, correction_obj.data['__all__'])
            need_to_be_corrected.remove('__all__')

        not_corrected = need_to_be_corrected - changed_fields
        if not_corrected:
            for field_name in not_corrected:
                self.add_error(field_name, l_('Нужно изменить требуемое поле'))
                self.add_error(field_name, correction_obj.data[field_name])

        return self.cleaned_data


class ApproveByAccountManagerForm(ModelForm):

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number'
        ]

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        current_version = kwargs.pop('current_version')
        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['current_version'].initial = current_version

        reviewed_version = None
        last_correction = self.instance.get_correction_last(get_task_ref(self.linked_node))
        if last_correction:
            reviewed_version = last_correction.reviewed_version

        fields_with_corrections = OrderedDict()
        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле
            if field_name == 'current_version':
                fields_with_corrections[field_name] = field
                continue

            # делаем поле неактивным
            field.widget.attrs['readonly'] = True
            fields_with_corrections[field_name] = field

            # если есть прошлые значения поля, которые изменились с момента последней проверки, выводим их на форму
            if reviewed_version and reviewed_version.field_dict[field_name] != self.initial[field_name]:
                field.help_text = 'Прошлое значение: {0}'.format(reviewed_version.field_dict[field_name])

            # добавляем корректирующее поле к каждому полю на форме
            correction_field_name = field_name + CORR_SUFFIX
            fields_with_corrections[correction_field_name] = forms.CharField(
                max_length=255,
                required=False,
                label=str(l_('Корректировка для поля ')) + str(field.label).lower()
            )
            # если есть прошлые корректировки, добавляем инфу о них в корректирующее поле
            if last_correction and field_name in last_correction.data:
                help_text = 'Прошлая корректировка: {0}'.format(last_correction.data[field_name])
                fields_with_corrections[correction_field_name].help_text = help_text

        # Поле non_field корректировки
        non_field_correction = forms.CharField(
            max_length=255,
            required=False,
            label=l_('Блокировка всей заявки без привязки к конкретному полю'),
        )
        if last_correction and '__all__' in last_correction.data:
            non_field_correction.help_text = 'Прошлая корректировка: {0}'.format(last_correction.data['__all__'])
        fields_with_corrections['__all__' + CORR_SUFFIX] = non_field_correction

        self.fields = fields_with_corrections

    def clean(self):
        self.cleaned_data = super().clean()

        # проверяем, последнюю ли версию заявки просматривал пользователь:
        last_version = self.instance.get_last_version()
        if last_version != self.cleaned_data['current_version']:
            raise ValidationError(
                'Не удалось сохранить форму, т.к. заявка уже изменилась. Обновите страницу.'
            )
        return self.cleaned_data
