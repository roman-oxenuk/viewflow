# -*- coding: utf-8 -*-
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext_lazy as l_
from django.contrib.auth import get_user_model

from reversion.models import Version
from viewflow.fields import get_task_ref

from michelin_bpm.main.models import ProposalProcess


CORR_SUFFIX = settings.CORRECTION_FIELD_SUFFIX
COMMENT_SUFFIX = settings.COMMENT_REQUEST_FIELD_SUFFIX


class ApproveForm(ModelForm):

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number'
        ]

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        self.show_corrections = kwargs.pop('show_corrections', [])
        current_version = kwargs.pop('current_version')
        self.can_create_corrections = kwargs.pop('can_create_corrections')

        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['current_version'].initial = current_version

        reviewed_version = None
        last_correction = self.instance.get_correction_last(get_task_ref(self.linked_node))
        if last_correction:
            reviewed_version = last_correction.reviewed_version

        fields_with_corrections = OrderedDict()

        # Добавляем non_field поля для корректировки
        for corr_data in self.can_create_corrections:
            non_field_correction = forms.CharField(
                max_length=255,
                required=False,
                label=corr_data['non_field_corr_label'],
            )
            fields_with_corrections['__all__' + corr_data['field_suffix']] = non_field_correction

        # Добавляем корректирующие поля для каждого поля
        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле или поле корректировки
            if field_name == 'current_version':
                fields_with_corrections[field_name] = field
                continue

            # делаем поле неактивным
            field.widget.attrs['readonly'] = True
            fields_with_corrections[field_name] = field

            for corr_data in self.can_create_corrections:
                # добавляем корректирующее поле к каждому полю на форме
                correction_field_name = field_name + corr_data['field_suffix']
                fields_with_corrections[correction_field_name] = forms.CharField(
                    max_length=255,
                    required=False,
                    label=str(corr_data['field_label_prefix']) + str(field.label).lower()
                )

        self.fields = fields_with_corrections

    def clean(self):
        self.cleaned_data = super().clean()

        # проверяем, последнюю ли версию заявки просматривал пользователь:
        last_version = self.instance.get_last_version()
        if last_version != self.cleaned_data['current_version']:
            raise ValidationError(
                'Не удалось сохранить форму, т.к. заявка уже изменилась. Обновите страницу.'
            )

        # Если даже в self.can_create_corrections указанна возможность создавать несколько Корректировок,
        # то всё равно после сохранения формы может быть создана Корректировка только одного вида.
        # Иначе мы не будем понимать, на какой шаг дальше отправить заявку.
        # correction_data = []
        # if len(self.can_create_corrections) > 1:
        #     for corr_settings in self.can_create_corrections:
        #         step_corr = dict([
        #             (name.replace(corr_settings['field_suffix'], ''), value)
        #             for name, value in self.cleaned_data.items()
        #             if name.endswith(corr_settings['field_suffix']) and value
        #         ])
        #         if step_corr:
        #             correction_data.append(step_corr)

        #     if len(correction_data) > 1:
        #         raise ValidationError('Можно создавать корректировки только одного вида.')

        return self.cleaned_data


class LogistForm(ApproveForm):

    class Meta:
        model = ProposalProcess
        fields = ['country', 'city', 'company_name']

    def clean(self):
        """ Проверяем, внёс ли Логист свою корректировку в ответ на корректировку Шефа """
        self.cleaned_data = super().clean()

        corrections_qs = self.instance.get_correction_active(for_step=get_task_ref(self.linked_node))
        # Для Логиста всегда должна быть одна активная Корретировка, т.к. он общается только с Шефом региона,
        # и только Шеф региона может создавать для него Корректировки.
        # TODO MBPM-3: Закрепить это на уровне констрейта в БД?
        correction_obj = corrections_qs.first()
        need_to_be_commented = set(correction_obj.data.keys())

        for corr_settings in self.can_create_corrections:
            commented_fields = set([
                field_name.replace(corr_settings['field_suffix'], '')
                for field_name in self.changed_data
                if field_name.endswith(corr_settings['field_suffix'])
            ])

        if '__all__' in need_to_be_commented:
            if not self.changed_data:
                msg = l_(
                    'Нужно обавить хотя бы один комментарий в соответствие с корретировкой: ' +
                    correction_obj.data['__all__']
                )
                self.add_error(None, msg)
            need_to_be_commented.remove('__all__')

        not_commented = need_to_be_commented - commented_fields
        if not_commented:
            for field_name in not_commented:
                self.add_error(field_name, l_('Нужно оставить комментарий для этого поля'))

        return self.cleaned_data


class FixMistakesForm(ModelForm):

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number'
        ]

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        super().__init__(*args, **kwargs)

    def clean(self):
        self.cleaned_data = super().clean()

        # Проверяем, изменились ли те поля, к которым были указаны корректировки
        # correction_obj = self.instance.get_correction_active(for_step=get_task_ref(self.linked_node))
        # need_to_be_corrected = set(correction_obj.data.keys())

        corrections_qs = self.instance.get_correction_active(for_step=get_task_ref(self.linked_node))
        # Для Клиента всегда должна быть одна активная Корретировка, т.к. он общается через Аккаунта,
        # и только Аккаунт может создавать для него Корректировки
        # TODO MBPM-3: Закрепить это на уровне констрейта в БД?
        correction_obj = corrections_qs.first()
        need_to_be_corrected = set(correction_obj.data.keys())

        last_version = correction_obj.reviewed_version
        changed_fields = set(
            self.instance.get_diff_fields(
                self.cleaned_data, last_version, self.fields.keys()
            ).keys()
        )

        if '__all__' in need_to_be_corrected:
            if not changed_fields:
                msg = l_(
                    'Нужно изменить хотя бы одно поле в соответствие с корретировкой: ' +
                    correction_obj.data['__all__']
                )
                self.add_error(None, msg)
            need_to_be_corrected.remove('__all__')

        not_corrected = need_to_be_corrected - changed_fields
        if not_corrected:
            for field_name in not_corrected:
                msg = l_(
                    'Нужно изменить это поле в соответствие с корректировкой: ' +
                    correction_obj.data[field_name]
                )
                self.add_error(field_name, msg)

        return self.cleaned_data


class AddJCodeADVForm(ModelForm):
    # TODO MBPM-3:
    # Добавить валидацию поле J-Code.
    # Проверять по шаблону или хотя бы по кол-ву символов.

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number', 'j_code'
        ]
        can_edit = ['j_code']

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        current_version = kwargs.pop('current_version')

        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['j_code'].required = True

        self.fields['current_version'].initial = current_version

        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле или поле корректировки
            if field_name == 'current_version':
                continue

            # делаем поле неактивным
            if field_name not in self.Meta.can_edit:
                field.widget.attrs['readonly'] = True


class AddBibServerDataForm(ModelForm):

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number',
            'bibserve_login', 'bibserve_password'
        ]
        can_edit = ['bibserve_login', 'bibserve_password']

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        current_version = kwargs.pop('current_version')

        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['bibserve_login'].required = True
        self.fields['bibserve_password'].required = True

        self.fields['current_version'].initial = current_version

        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле или поле корректировки
            if field_name == 'current_version':
                continue

            # делаем поле неактивным
            if field_name not in self.Meta.can_edit:
                field.widget.attrs['readonly'] = True


class SetCreditLimitForm(ModelForm):

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number'
        ]
        can_edit = []

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        current_version = kwargs.pop('current_version')

        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['current_version'].initial = current_version

        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле или поле корректировки
            if field_name == 'current_version':
                continue

            # делаем поле неактивным
            if field_name not in self.Meta.can_edit:
                field.widget.attrs['readonly'] = True


class UnblockClientForm(ModelForm):

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number'
        ]
        can_edit = []

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        current_version = kwargs.pop('current_version')

        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['current_version'].initial = current_version

        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле или поле корректировки
            if field_name == 'current_version':
                continue

            # делаем поле неактивным
            if field_name not in self.Meta.can_edit:
                field.widget.attrs['readonly'] = True


class AddACSForm(ModelForm):

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number', 'acs'
        ]
        can_edit = ['acs']

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        current_version = kwargs.pop('current_version')

        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['current_version'].initial = current_version

        User = get_user_model()
        self.fields['acs'].queryset = User.objects.filter(groups__name='ASC')

        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле или поле корректировки
            if field_name == 'current_version':
                continue

            # делаем поле неактивным
            if field_name not in self.Meta.can_edit:
                field.widget.attrs['readonly'] = True


class ActivateBibserveAccountForm(ModelForm):

    current_version = forms.ModelChoiceField(queryset=None, widget=forms.HiddenInput())

    class Meta:
        model = ProposalProcess
        fields = [
            'country', 'city', 'company_name', 'inn',
            'bank_name', 'account_number'
        ]
        can_edit = []

    def __init__(self, *args, **kwargs):
        self.linked_node = kwargs.pop('linked_node')
        current_version = kwargs.pop('current_version')

        super().__init__(*args, **kwargs)

        self.fields['current_version'].queryset = Version.objects.get_for_object(self.instance)
        self.fields['current_version'].initial = current_version

        for field_name, field in self.fields.items():

            # пропускаем спрятанное служебное поле или поле корректировки
            if field_name == 'current_version':
                continue

            # делаем поле неактивным
            if field_name not in self.Meta.can_edit:
                field.widget.attrs['readonly'] = True
