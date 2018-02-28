# -*- coding: utf-8 -*-
import json
import os

from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.forms.models import model_to_dict
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views import View

import reversion
from reversion.models import Version
from viewflow.flow.views.task import UpdateProcessView
from viewflow.flow.views import CreateProcessView
from viewflow.fields import get_task_ref
from viewflow.frontend.views import ProcessListView

from michelin_bpm.main.models import ProposalProcess, Correction, BibServeProcess


CORR_SUFFIX = settings.CORRECTION_FIELD_SUFFIX
COMMENT_SUFFIX = settings.COMMENT_REQUEST_FIELD_SUFFIX


class ProposalExcelDocumentView(View):
    def get(self, request):
        path = '{}/static/main/proposal-info.xlsx'.format(os.path.abspath(os.path.dirname(__file__)))
        # path = staticfiles_storage.url('main/proposal-info.xlsx')
        with open(path, 'rb') as excel:
            data = excel.read()

            response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=proposal-info.xlsx'
            return response


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
        # {'for_step': '', 'made_on_step': ''}
        # добавляем имя своего шага, чтобы видеть корректировки, созданные для этого шага
        for_steps.append(
            {'for_step': get_task_ref(self.linked_node)}
        )
        # добавляем возможность видеть корректировки для других шагов, если это настроенно в ноде
        for corr_setting in self.show_corrections:
            for_steps.append({
                'for_step': get_task_ref(corr_setting['for_step']),
                'made_on_step': get_task_ref(corr_setting['made_on_step']) if ('made_on_step' in corr_setting) else None
            })
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
                    'from_step_obj': correction.task.flow_task,
                    'owner': str(correction.owner),
                    'created': correction.created,
                    'is_active': correction.is_active,
                    'changed_fieldschanged_fields': None,
                }
                if '__all__' in fields_corrections:
                    fields_corrections['__all__'].append(non_field_corr)
                else:
                    fields_corrections['__all__'] = [non_field_corr]

                if correction.fixed_in_version:
                    base_instace = json.loads(correction.fixed_in_version.serialized_data)[0]['fields']
                    diff = ProposalProcess.get_diff_fields(
                        base_instace,
                        correction.reviewed_version,
                        fields
                    )
                    non_field_corr['changed_fields'] = diff
                    for (changed_field_name, changed_field_old_value) in diff.items():
                        field_corr = {
                            'msg': correction.data['__all__'],
                            'from_step': str(correction.task.flow_task),
                            'from_step_obj': correction.task.flow_task,
                            'owner': str(correction.owner),
                            'created': correction.created,
                            'is_active': correction.is_active,
                            'version_value': None
                        }
                        if correction.fixed_in_version:
                            field_corr['version_value'] = changed_field_old_value['old_value']
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
                        'from_step_obj': correction.task.flow_task,
                        'owner': str(correction.owner),
                        'created': correction.created,
                        'is_active': correction.is_active,
                        'version_value': None,
                    }
                    if correction.fixed_in_version:
                        base_instace = json.loads(correction.fixed_in_version.serialized_data)[0]['fields']

                        diff = ProposalProcess.get_diff_fields(
                            base_instace,
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'fields_corrections': self.get_fields_corrections(self.get_object())
        })
        return kwargs


class ActionTitleMixin:

    action_title = None

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['action_title'] = self.action_title
        return context_data


class ApproveView(ActionTitleMixin, ShowCorrectionsMixin, UpdateProcessView):

    linked_node = None      # инстанс viewflow.Node, к которому прикреплён текущий View
    can_create_corrections = []   # Корректировки для каких шагов могут быть созданный в рамках этого View
    show_corrections = []   # Какие дополнительные Корректировки могут быть показаны кроме тех,
                            # что созданны для текущего шага self.linked_node

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['action_title'] = self.action_title
        return context_data

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
        corrections_qs = form.instance.get_correction_active(
            for_step=get_task_ref(self.linked_node)
        )
        corrections_qs.update(is_active=False)

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


class FixMistakesView(ActionTitleMixin, ShowCorrectionsMixin, UpdateProcessView):

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


class AddDataView(ActionTitleMixin, UpdateProcessView):

    linked_node = None      # инстанс viewflow.Node, к которому прикреплён текущий View

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
        })
        return kwargs

    def form_valid(self, form, *args, **kwargs):
        with reversion.create_revision():
            super().form_valid(form, **kwargs)
            reversion.set_user(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class AddJCodeView(AddDataView):

    def form_valid(self, form, *args, **kwargs):
        if form.instance.is_needs_bibserve_account:
            from michelin_bpm.main.flows import BibServeFlow
            BibServeFlow.start.run(form.instance)
        return super().form_valid(form, *args, **kwargs)


class SeeDataView(ActionTitleMixin, UpdateProcessView):

    linked_node = None      # инстанс viewflow.Node, к которому прикреплён текущий View

    template_name = 'main/proposalconfirmation/task_downloadable.html'

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
        })
        return kwargs


class BibServerAccountMixin:

    def get_object(self, queryset=None):
        return self.activation.process.bibserveprocess.proposal


class CreateBibServerAccountView(BibServerAccountMixin, SeeDataView):
    pass


class ActivateBibServeAccountView(BibServerAccountMixin, AddDataView):
    pass


class UnblockClientView(SeeDataView):

    def form_valid(self, form, *args, **kwargs):
        from michelin_bpm.main.signals import client_unblocked
        client_unblocked.send(sender=self.__class__, proposal=form.instance)
        return super().form_valid(form, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class MichelinProcessListView(ProcessListView):

    def get_queryset(self):
        queryset = super().get_queryset()
        is_client = self.request.user.groups.filter(name='Клиенты').exists()
        if is_client:
            if queryset.model == ProposalProcess:
                queryset = queryset.filter(client=self.request.user)

            if queryset.model == BibServeProcess:
                queryset = queryset.filter(proposal__client=self.request.user)

        return queryset
