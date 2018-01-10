# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from viewflow.flow.views.task import UpdateProcessView, FlowMixin
from viewflow.flow.views import CreateProcessView
from viewflow.flow.views.start import StartFlowMixin

from .models import Correction


class CreateProposalProcessView(CreateProcessView):

    def form_valid(self, *args, **kwargs):
        super(StartFlowMixin, self).form_valid(*args, **kwargs)
        self.activation.process.client = self.request.user
        self.activation_done(*args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class ApproveByAccountManagerView(UpdateProcessView):

    def form_valid(self, *args, **kwargs):
        """ Создаёт объект Корректировки, если есть поля с заполненными корректировками """
        super(FlowMixin, self).form_valid(*args, **kwargs)
        form = self.get_form()
        correction_data = dict([
            (name, value) for name, value in form.data.items()
            if name.endswith('_correction') and value
        ])
        if correction_data:
            Correction.objects.create(
                task=self.activation.task,
                data=correction_data,
                is_active=True,
                owner=self.request.user
            )
        self.activation_done(*args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class FixMistakesView(UpdateProcessView):

    mistakes_from_step = None

    def __init__(self, *args, **kwargs):  # noqa D102
        self._mistakes_from_step = kwargs.pop('mistakes_from_step', None)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(client=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'process_pk': self.kwargs['process_pk']
        })
        if self._mistakes_from_step:
            kwargs.update({
                'mistakes_from_step': self._mistakes_from_step
            })
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class=None)
        # Добавляем информацию о корректировках для полей
        if self.request.method == 'GET' and form.instance:
            corrections = form.instance.get_corrected_fields(from_step=self._mistakes_from_step)

            for field_name, field in form.fields.items():
                correction_name = '{0}_correction'.format(field_name)
                if correction_name in corrections:
                    for corr in corrections[correction_name]:
                        try:
                            form.add_error(field_name, corr)
                        except AttributeError:
                            pass
        return form

    def form_valid(self, form, **kwargs):
        """ Деактивируем объект Корректировки, если произошло изменение блокирующих полей """
        super(FlowMixin, self).form_valid(form, **kwargs)
        # TODO MBPM-3
        # Сделать изменение одним запросом, если это возможно
        for task in form.instance.task_set.filter(correction__is_active=True, flow_task=self._mistakes_from_step):
            task.correction_set.all().filter(is_active=True).update(is_active=False)

        self.activation_done(**kwargs)
        return HttpResponseRedirect(self.get_success_url())
