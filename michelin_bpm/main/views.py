# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.conf import settings

import reversion
from reversion.views import RevisionMixin
from reversion.models import Version
from viewflow.flow.views.task import UpdateProcessView, FlowMixin
from viewflow.flow.views import CreateProcessView
from viewflow.fields import get_task_ref

from michelin_bpm.main.models import Correction


CORR_SUFFIX = settings.CORRECTION_FIELD_SUFFIX


class CreateProposalProcessView(RevisionMixin, CreateProcessView):

    linked_node = None

    def form_valid(self, *args, **kwargs):
        reversion.set_comment(get_task_ref(self.linked_node))
        self.activation.process.client = self.request.user
        super().form_valid(*args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class ApproveByAccountManagerView(UpdateProcessView):

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
            'linked_node': self.linked_node
        })

        return kwargs

    def form_valid(self, form, *args, **kwargs):
        """ Создаёт объект Корректировки, если есть поля с заполненными корректировками """
        correction_data = dict([
            (name.replace(CORR_SUFFIX, ''), value) for name, value in form.cleaned_data.items()
            if name.endswith(CORR_SUFFIX) and value
        ])
        if correction_data:
            Correction.objects.create(
                task=self.activation.task,
                proposal=self.activation.process,
                reviewed_version=form.cleaned_data['current_version'],
                data=correction_data,
                is_active=True,
                owner=self.request.user
            )
        super().form_valid(form, *args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class FixMistakesView(RevisionMixin, UpdateProcessView):

    mistakes_from_step = None

    def get_queryset(self):
        proposal_qs = super().get_queryset()
        return proposal_qs.filter(client=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'process_pk': self.kwargs['process_pk']
        })
        if self.mistakes_from_step:
            kwargs.update({
                'mistakes_from_step': self.mistakes_from_step
            })
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Добавляем информацию о корректировках для полей
        if self.request.method == 'GET' and form.instance:
            correction_obj = form.instance.get_correction_active(for_step=self.mistakes_from_step)
            for field_name, corr in correction_obj.data.items():
                if field_name in form.errors:
                    form.errors[field_name].append(corr)
                else:
                    form.errors[field_name] = form.error_class([corr])
        return form

    def form_valid(self, form, **kwargs):
        """ Деактивируем объект Корректировки, если произошло изменение блокирующих полей """
        reversion.set_comment(self.mistakes_from_step)

        correction_obj = form.instance.get_correction_active(for_step=self.mistakes_from_step)
        correction_obj.is_active = False
        correction_obj.save()

        super().form_valid(form, **kwargs)
        return HttpResponseRedirect(self.get_success_url())
