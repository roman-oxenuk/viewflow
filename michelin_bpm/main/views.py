# -*- coding: utf-8 -*-
import json

from django.http import HttpResponseRedirect
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView
from django.utils.translation import ugettext_lazy as _
import reversion
from reversion.models import Version

from viewflow.flow.views.task import UpdateProcessView
from viewflow.flow.views import CreateProcessView
from viewflow.fields import get_task_ref
from viewflow.frontend.views import ProcessListView
from michelin_bpm.main.models import ProposalProcess, Correction, BibServeProcess
from michelin_bpm.main.forms import ClientSetPasswordForm


class EnterClientPasswordView(PasswordResetConfirmView):

    template_name = 'main/registration/password_reset_confirm.html'
    title = _('Enter password')
    form_class = ClientSetPasswordForm
    post_reset_login = True
    success_url = '/'

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect('/')
        return super().dispatch(*args, **kwargs)


class ActionTitleMixin:
    """
    Миксин, передающий done_btn_title в форму.
    done_btn_title -- надпись на той кнопке, которая переводит заявку на следующий шаг.
    """
    done_btn_title = None

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['done_btn_title'] = self.done_btn_title
        return context_data


class VersionViewMixin:
    """
    Миксин, передающий в форму текущую версию заявки.
    Версия нужна для того, чтобы понимать,
    к какой версии Заявки был добавлен комментарий (или какая версия Заявки была согласована).
    """
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        current_version = Version.objects.get_for_object(
            kwargs['instance']
        ).order_by(
            '-revision__date_created'
        ).first()

        kwargs.update({'current_version': current_version})
        return kwargs


class BaseView(VersionViewMixin, ActionTitleMixin):
    pass


class CreateProposalProcessView(CreateProcessView):

    linked_node = None

    def form_valid(self, *args, **kwargs):
        with reversion.create_revision():
            super().form_valid(*args, **kwargs)
            reversion.set_user(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ShowCorrectionsMixin:

    linked_node = None

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
            'fields_corrections': self.get_fields_corrections(self.get_object()),
            'linked_node': self.linked_node
        })
        return kwargs


class ApproveView(BaseView, ShowCorrectionsMixin, UpdateProcessView):
    """
    Вью для согласования заявки.
    Аттрибуты вью:
    linked_node -- инстанс viewflow.Node, к которому прикреплён текущий ApproveView.
                    При создании Корректировки в поле Correction.for_step сохраняется linked_node,
                    закодированный через viewflow.fields.get_task_ref().
                    Поэтому в дальнейшем по полю Correction.for_step мы можем фильтровать Корректировки.
                    Например чтобы показывать только те, которые определены в ApproveView.show_corrections.
    can_create_corrections -- Корректировки для каких шагов могут быть созданный в рамках этого ApproveView.
    show_corrections -- какие дополнительные Корректировки могут быть показаны.
                        Кроме тех, что созданны для текущего шага, опередённого в self.linked_node.
    """
    linked_node = None
    can_create_corrections = []
    show_corrections = []

    def get_available_actions(self):
        return [corr_settings['action_btn_name'] for corr_settings in self.can_create_corrections]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        # Если форма отправлена по нажатию какой-то кнопки, кроме "done",
        # то это предполагает, что пользователь оставил комментарий к заявке.
        # Поэтому поле для с соответствующим комментарием должно быть обязательно заполнено.
        actions = self.get_available_actions()
        applied_actions = set(actions) & set(request.POST)
        if applied_actions:
            for act in applied_actions:
                for field_name, field in form.fields.items():
                    if field_name.endswith(act):
                        field.required = True

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'can_create_corrections': self.can_create_corrections,
            'show_corrections': self.show_corrections,
            'linked_node': self.linked_node,
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
                (name.replace(corr_settings['action_btn_name'], ''), value)
                for name, value in form.cleaned_data.items()
                if name.endswith(corr_settings['action_btn_name']) and value
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


class FixMistakesView(BaseView, ShowCorrectionsMixin, UpdateProcessView):

    show_corrections = []

    def get_queryset(self):
        proposal_qs = super().get_queryset()
        return proposal_qs.filter(client=self.request.user)

    def form_valid(self, form, **kwargs):
        with reversion.create_revision():
            super().form_valid(form, **kwargs)
            reversion.set_user(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class SeeDataView(BaseView, UpdateProcessView):
    """
    Вью, просто показывающее данные в Заявке.
    Применяется, например, для случая, когда пользователь должен перенести данные из Заявки в другие системы.
    """
    pass


class AddDataView(SeeDataView):
    """
    Вью, в котором пользователь добавляет какие-то данные к заявке.
    """
    def form_valid(self, form, *args, **kwargs):
        with reversion.create_revision():
            super().form_valid(form, **kwargs)
            reversion.set_user(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ClientAddDataView(AddDataView):
    pass


class AddJCodeView(AddDataView):

    def form_valid(self, form, *args, **kwargs):
        if form.instance.is_needs_bibserve_account:
            from michelin_bpm.main.flows import BibServeFlow
            BibServeFlow.start.run(form.instance)
        return super().form_valid(form, *args, **kwargs)


class UnblockClientView(SeeDataView):

    def form_valid(self, form, *args, **kwargs):
        from michelin_bpm.main.signals import client_unblocked
        client_unblocked.send(sender=self.__class__, proposal=form.instance)
        return super().form_valid(form, *args, **kwargs)


class BibServerAccountMixin:

    def get_object(self, queryset=None):
        return self.activation.process.bibserveprocess.proposal


class CreateBibServerAccountView(BibServerAccountMixin, SeeDataView):
    pass


class ActivateBibServeAccountView(BibServerAccountMixin, AddDataView):
    pass


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
