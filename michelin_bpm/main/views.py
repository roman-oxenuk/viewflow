# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.conf import settings
from django.forms.models import model_to_dict

import reversion
from reversion.models import Version
from viewflow.flow.views.task import UpdateProcessView
from viewflow.flow.views import CreateProcessView
from viewflow.fields import get_task_ref

from michelin_bpm.main.models import ProposalProcess, Correction


CORR_SUFFIX = settings.CORRECTION_FIELD_SUFFIX
COMMENT_SUFFIX = settings.COMMENT_REQUEST_FIELD_SUFFIX


class CreateProposalProcessView(CreateProcessView):

    linked_node = None

    def form_valid(self, *args, **kwargs):
        self.activation.process.client = self.request.user

        with reversion.create_revision():
            super().form_valid(*args, **kwargs)
            reversion.set_user(self.request.user)

        return HttpResponseRedirect(self.get_success_url())


class ShowCorrectionsMixin:

    def get_fields_corrections(self, instance):
        """
        Возвращает dict с ключами с именем полей и значениями в виде Корректировок и историй изменений заявки.
        На основании show_corrections и полей формы.
        """
        for_steps = []
        # добавляем имя своего шага, чтобы видеть корректировки, созданные для этого шага
        for_steps.append(get_task_ref(self.linked_node))
        # добавляем возможность видеть корректировки для других шагов, если это настроенно в ноде
        for corr_setting in self.show_corrections:
            for_steps.append(get_task_ref(corr_setting['for_step']))
        corrections_qs = instance.get_corrections_all(for_steps)

        # Поля, которые видит пользователь в рамках этого view
        fields = self.fields
        if not fields:
            fields = self.form_class.base_fields.keys()
            fields = [name for (name, field) in self.form_class.base_fields.items()]

        fields_corrections = {}

        # Добавляем non_field поле
        for correction in corrections_qs:
            if '__all__' in correction.data:
                non_field_corr = {
                    'msg': correction.data['__all__'],
                    'from_step': str(correction.task.flow_task),
                    'owner': str(correction.owner),
                    'created': correction.created,
                    'is_active': correction.is_active,
                    'version_value': None,
                }
                if '__all__' in fields_corrections:
                    fields_corrections['__all__'].append(non_field_corr)
                else:
                    fields_corrections['__all__'] = [non_field_corr]

                diff = ProposalProcess.get_diff_fields(
                    model_to_dict(instance),
                    correction.reviewed_version,
                    fields
                )
                for (changed_field_name, changed_field_old_value) in diff.items():
                    field_corr = {
                        'msg': correction.data['__all__'],
                        'from_step': str(correction.task.flow_task),
                        'owner': str(correction.owner),
                        'created': correction.created,
                        'is_active': correction.is_active,
                        'version_value': changed_field_old_value['old_value'],
                    }
                    if changed_field_name in fields_corrections:
                        fields_corrections[changed_field_name].append(field_corr)
                    else:
                        fields_corrections[changed_field_name] = [field_corr]

        for field_name in fields:
            for correction in corrections_qs:
                if field_name in correction.data:
                    field_corr = {
                        'msg': correction.data[field_name],
                        'from_step': str(correction.task.flow_task),
                        'owner': str(correction.owner),
                        'created': correction.created,
                        'is_active': correction.is_active,
                        'version_value': None,
                    }

                    diff = ProposalProcess.get_diff_fields(
                        model_to_dict(instance),
                        correction.reviewed_version,
                        [field_name]
                    )
                    if diff:
                        field_corr['version_value'] = diff[field_name]['old_value']

                    if field_name in fields_corrections:
                        fields_corrections[field_name].append(field_corr)
                    else:
                        fields_corrections[field_name] = [field_corr]

        return fields_corrections

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['fields_corrections'] = self.get_fields_corrections(self.get_object())
        return context_data


class ApproveView(ShowCorrectionsMixin, UpdateProcessView):

    linked_node = None      # инстанс viewflow.Node, к которому прикреплён текущий View
    can_create_corrections = []   # Корректировки для каких шагов могут быть созданный в рамках этого View
    show_corrections = []   # Какие дополнительные Корректировки могут быть показаны кроме тех,
                            # что созданны для текущего шага self.linke_node

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        current_version = Version.objects.get_for_object(
            kwargs['instance']
        ).order_by(
            '-revision__date_created'
        ).first()

        kwargs.update({
            'current_version': current_version,
            'linked_node': self.linked_node,
            'can_create_corrections': self.can_create_corrections,
            'show_corrections': self.show_corrections,
        })
        return kwargs

    def form_valid(self, form, *args, **kwargs):
        """ Создаёт объект Корректировки, если есть поля с заполненными корректировками """

        # Деактивируем корректировку для нашего текущего шага
        correction_obj = form.instance.get_correction_active(
            for_step=get_task_ref(self.linked_node)
        )
        if correction_obj:
            correction_obj.is_active = False
            correction_obj.save()

        # TODO MBPM-3: Вынести запрос к БД из цикла
        for corr_settings in self.can_create_corrections:
            correction_data = dict([
                (name.replace(corr_settings['field_suffix'], ''), value)
                for name, value in form.cleaned_data.items()
                if name.endswith(corr_settings['field_suffix']) and value
            ])
            if correction_data:
                Correction.objects.create(
                    task=self.activation.task,
                    proposal=self.activation.process,
                    for_step=get_task_ref(corr_settings['for_step']),
                    reviewed_version=form.cleaned_data['current_version'],
                    data=correction_data,
                    is_active=True,
                    owner=self.request.user
                )

        super().form_valid(form, *args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class FixMistakesView(ShowCorrectionsMixin, UpdateProcessView):

    linked_node = None
    show_corrections = []

    def get_queryset(self):
        proposal_qs = super().get_queryset()
        return proposal_qs.filter(client=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'linked_node': self.linked_node})
        return kwargs

    def form_valid(self, form, **kwargs):
        with reversion.create_revision():
            super().form_valid(form, **kwargs)
            reversion.set_user(self.request.user)
        return HttpResponseRedirect(self.get_success_url())
