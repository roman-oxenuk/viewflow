# -*- coding: utf-8 -*-
import os
import json

from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView
from django.utils.translation import ugettext_lazy as _
from django.utils.html import mark_safe
from django.urls import reverse
from django.views.generic.edit import UpdateView
from django.views import View
from django.utils.translation import ugettext_lazy as l_

import reversion
from reversion.models import Version

from viewflow.flow.views.task import UpdateProcessView
from viewflow.flow.views import CreateProcessView
from viewflow.fields import get_task_ref
from viewflow.frontend.views import ProcessListView
from michelin_bpm.main.models import ProposalProcess, Correction, BibServeProcess, DeliveryAddress
from michelin_bpm.main.forms import ClientSetPasswordForm, DeliveryAddressForm
from michelin_bpm.main.utils import render_excel_template


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


class StopProposalMixin:

    _is_stopped = None

    def is_proposal_stopped(self):
        if self._is_stopped is None:
            active_corr_for_client = self.get_object().get_correction_active(
                for_step='main/flows.ProposalConfirmationFlow.fix_mistakes_after_account_manager'
            )
            self._is_stopped = active_corr_for_client.exists()
        return self._is_stopped

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        if self.is_proposal_stopped():
            context_data['done_btn_title'] = None
            context_data['is_stopped'] = True
        return context_data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.is_proposal_stopped():
            if 'can_create_corrections' in kwargs:
                kwargs['can_create_corrections'] = []
        return kwargs


from viewflow.decorators import flow_view
class ProposalExcelDocumentView(View):
    def get(self, request, proposal_id=None):
        # if not proposal_id:
        #     return HttpResponseBadRequest()

        # TODO MBPM-3:
        # Добавить тут валидацию на существующую Заявку и на то, что задача по ней пренадлежит этому пользователю.
        # И вообще заявка должна браться из activation
        p = ProposalProcess.objects.get(pk=proposal_id) if proposal_id else ProposalProcess.objects.first()  # for testing
        template_path = '{}/static/main/proposal-info.xls'.format(os.path.abspath(os.path.dirname(__file__)))
        context = {
            (1, 0): p.company_name,
            (1, 8): p.date.strftime('%d/%m/%Y'),
            (3, 0): p.operation_type_name,
            (10, 1): p.jur_form,
            (10, 5): p.client_name,

            (17, 4): p.jur_zip_code,
            (17, 7): p.jur_country,
            (18, 3): p.jur_region,
            (18, 7): p.jur_city,
            (19, 1): p.jur_street,
            (19, 5): p.jur_building,
            (19, 7): p.jur_block,
            (20, 1): p.inn,
            (20, 3): p.kpp,
            (20, 5): p.okpo,
            (20, 7): p.ogrn,

            (23, 2): p.bank_details,
            (24, 1): p.bik,
            (24, 3): p.corr_account_number,
            (25, 2): p.account_number,

            (27, 3): p.contract_number,
            (27, 6): p.contract_date.strftime('%d/%m/%Y') if p.contract_date else '',

            (29, 4): p.zip_code,
            (29, 7): p.country,
            (30, 3): p.region,
            (30, 7): p.city,
            (31, 1): p.street,
            (31, 5): p.building,
            (31, 7): p.block,

            (32, 3): p.dir_name,
            (32, 7): p.dir_tel,
            (33, 1): p.dir_email,
            (33, 7): p.dir_fax,

            (34, 2): p.buh_name,
            (34, 7): p.buh_tel,
            (35, 1): p.buh_email,
            (35, 7): p.buh_fax,

            (36, 2): p.contact_name,
            (36, 7): p.contact_tel,
            (37, 1): p.contact_email,
            (37, 7): p.contact_fax,

            (39, 8): l_('Да') if p.is_needs_bibserve_account else l_('Нет'),
            (40, 2): p.bibserve_login,
            (41, 1): p.bibserve_email,
            (41, 7): p.bibserve_tel,

            (43, 5): p.delivery_client_name,
            (44, 4): p.delivery_zip_code,
            (44, 7): p.delivery_country,
            (45, 3): p.delivery_region,
            (45, 7): p.delivery_city,
            (46, 1): p.delivery_street,
            (46, 5): p.delivery_building,
            (46, 7): p.delivery_block,
            (47, 3): p.delivery_contact_name,
            (47, 7): p.delivery_tel,
            (48, 7): p.delivery_fax,
            (49, 5): p.delivery_email,

            (53, 4): p.warehouse_working_hours_from,
            (53, 6): p.warehouse_working_hours_to,
            (54, 4): p.warehouse_break_from,
            (54, 6): p.warehouse_break_to,
            (56, 2): p.warehouse_comment,
            (59, 2): p.warehouse_consignee_code,
            (60, 2): p.warehouse_station_code,
            (58, 7): p.warehouse_tc,
            (59, 7): p.warehouse_pl,
            (60, 7): p.warehouse_gc,
            (61, 7): p.warehouse_ag,
            (62, 7): p.warehouse_2r,

            (65, 0): p.company_name,
        }

        path = '{}proposal-info/'.format(settings.MEDIA_ROOT)
        os.makedirs(path, exist_ok=True)
        path = '{}proposal-{}.xls'.format(path, p.pk)

        render_excel_template(template_path, context, path)

        with open(path, 'rb') as excel:
            data = excel.read()

            response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=proposal-info.xls'
            return response

    @method_decorator(flow_view)
    def dispatch(self, request, *args, **kwargs):
        """Check permissions and show task detail."""
        self.activation = request.activation

        if not self.activation.flow_task.can_view(request.user, self.activation.task):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CreateProposalProcessView(ActionTitleMixin, CreateProcessView):

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


class ApproveView(StopProposalMixin, BaseView, ShowCorrectionsMixin, UpdateProcessView):
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


class SeeDataView(StopProposalMixin, BaseView, UpdateProcessView):
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
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_show_approving_data_checkbox'] = True
        DeliveryFormset = inlineformset_factory(ProposalProcess, DeliveryAddress, form=DeliveryAddressForm, extra=0)
        context['formset'] = DeliveryFormset(instance=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        DeliveryFormset = inlineformset_factory(ProposalProcess, DeliveryAddress, form=DeliveryAddressForm)
        formset = DeliveryFormset(request.POST, instance=self.get_object())

        if form.is_valid() and formset.is_valid():
            formset.save()
            return self.form_valid(form)
        return self.form_invalid(form)


class ClientPrintProposalView(AddDataView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_downloadable'] = True
        return context


class DownloadCardView(AddDataView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['downloadable_btn_label'] = _('Download OIZ Card')
        return context


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


from michelin_bpm.main.forms import all_fields
class ProposalDetailView(UpdateView):

    model = ProposalProcess
    pk_url_kwarg = 'proposal_pk'
    template_name = 'main/proposalconfirmation/show_proposal.html'
    fields = all_fields

    def get_queryset(self):
        queryset = super().get_queryset()
        is_client = self.request.user.groups.filter(id=settings.CLIENTS_GROUP_ID).exists()
        if is_client:
            queryset = queryset.filter(client=self.request.user)
        return queryset

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs['readonly'] = True
        return form


@method_decorator(login_required, name='dispatch')
class MichelinProcessListView(ProcessListView):

    list_display = [
        'process_id', 'process_summary', 'proposal_link',
        'created', 'finished', 'active_tasks'
    ]

    def process_summary(self, process):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse('proposal_detail', kwargs={'proposal_pk': process.pk}),
            process.summary())
        )
    process_summary.short_description = _('Proposal')

    def proposal_link(self, process):
        return mark_safe('<a href="{}">{}</a>'.format(
            self.get_process_link(process),
            _('Process')
        ))
    proposal_link.short_description = _('Process')

    def get_queryset(self):
        queryset = super().get_queryset()
        is_client = self.request.user.groups.filter(name='Клиенты').exists()
        if is_client:
            if queryset.model == ProposalProcess:
                queryset = queryset.filter(client=self.request.user)

            if queryset.model == BibServeProcess:
                queryset = queryset.filter(proposal__client=self.request.user)

        return queryset
