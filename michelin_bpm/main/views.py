# -*- coding: utf-8 -*-
import datetime
import os
import locale
import calendar
import logging
import json
from templated_docs import fill_template

from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView
from django.utils.translation import ugettext_lazy as _
from django.utils.html import mark_safe
from django.urls import reverse
from django.views.generic.edit import UpdateView
from django.views import View
from django.utils.translation import ugettext_lazy as l_
from django.template.response import TemplateResponse

import reversion
from reversion.models import Version

from viewflow.decorators import flow_view
from viewflow.flow.views.task import UpdateProcessView
from viewflow.flow.views import CreateProcessView
from viewflow.flow.views.detail import DetailProcessView
from viewflow.fields import get_task_ref
from viewflow.frontend.views import ProcessListView

from michelin_bpm.main.models import ProposalProcess, Correction, BibServeProcess, DeliveryAddress
from michelin_bpm.main.forms import (
    ClientSetPasswordForm, ShowProposalForm, DeliveryAddressForm, all_fields, DeliveryAddressReadonlyForm
)
from michelin_bpm.main.utils import render_excel_template


logger = logging.getLogger(__name__)


class DeliveryFormsetMixin(object):
    delivery_form = DeliveryAddressReadonlyForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        DeliveryFormset = inlineformset_factory(
            ProposalProcess, DeliveryAddress, form=self.delivery_form, extra=0, can_delete=False)
        context['delivery_formset'] = DeliveryFormset(instance=self.get_object())
        if getattr(self.delivery_form, 'readonly', None):
            context['delivery_formset_readonly'] = True
        return context

    def get_delivery_formset(self, data):
        DeliveryFormset = inlineformset_factory(
            ProposalProcess, DeliveryAddress, form=self.delivery_form, extra=0, can_delete=False)
        return DeliveryFormset(data, instance=self.get_object())


class EnterClientPasswordView(PasswordResetConfirmView):

    template_name = 'main/registration/password_reset_confirm.html'
    title = _('Enter password')
    form_class = ClientSetPasswordForm
    post_reset_login = True
    success_url = '/'

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect('/')

        response = super().dispatch(*args, **kwargs)

        if (not self.validlink and
                hasattr(response, 'context_data') and
                response.context_data['form'] is None):
            return HttpResponseRedirect('/')

        return response


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


class ProposalPdfContractView(View):
    """Договор в формате pdf.
    apt-get install libffi-dev
    apt-get install libreoffice (version >= 5)
    apt-get install locales
    Uncomment ru_RU.UTF-8 in /etc/locale.gen,
    then run 'locale-gen' for generating russian locale (need for month name).
    Add templated_docs to INSTALLED_APPS
    """
    def get(self, request):
        # if not proposal_id:
        #     return HttpResponseBadRequest()

        # import ipdb; ipdb.set_trace()

        # p = ProposalProcess.objects.get(pk=proposal_id) if proposal_id else ProposalProcess.objects.first()  # for testing
        p = self.activation.process
        da = p.deliveryaddress_set.first()

        try:
            locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        except locale.Error as err:
            logger.error('Can\'t set russian locale (get month name)!')
        contract_month_name = calendar.month_name[p.contract_date.month] if p.contract_date else ''

        def get_full_address(list_of_parts):
            return ', '.join(filter(bool, list_of_parts))

        context = vars(p)
        context = {k: (v if v else '') for k, v in context.items()}
        more = {
            'p': p,
            'pcd': p.contract_date.day if p.contract_date else '',
            'pcm': contract_month_name,
            'pcy': p.contract_date.year if p.contract_date else '',
            'full_address': get_full_address([p.zip_code, p.country, p.region, p.city, p.street, p.building, p.block]),
            'jur_full_address': get_full_address([p.jur_zip_code, p.jur_country, p.jur_region, p.jur_city,
                                                  p.jur_street, p.jur_building, p.jur_block]),
            'delivery_full_address': get_full_address([da.delivery_zip_code, da.delivery_country, da.delivery_region,
                                                       da.delivery_city, da.delivery_street, da.delivery_building,
                                                       da.delivery_block]) if da else '',
        }
        context = {**context, **more}
        filename = fill_template('main/contract.odt', context, output_format='pdf')

        with open(filename, 'rb') as excel:
            data = excel.read()

            response = HttpResponse(data, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=contract.pdf'
            return response

    @method_decorator(flow_view)
    def dispatch(self, request, *args, **kwargs):
        """Check permissions and show task detail."""
        self.activation = request.activation

        if not self.activation.flow_task.can_view(request.user, self.activation.task):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ProposalExcelDocumentView(View):
    """Заявка в формате excel."""
    def get(self, request):
        # TODO MBPM-3:
        # Добавить тут валидацию на существующую Заявку и на то, что задача по ней пренадлежит этому пользователю.
        # И вообще заявка должна браться из activation
        # proposal_id = 3
        # p = ProposalProcess.objects.get(pk=proposal_id) if proposal_id else ProposalProcess.objects.first()  # for testing
        p = self.activation.process

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

            (65, 0): p.company_name,
        }

        offset = [43, 108, 132, 156, 180]
        for i, da in enumerate(p.deliveryaddress_set.order_by('pk').all()[:5]):
            context.update({
                (offset[i], 5): da.delivery_client_name,
                (offset[i] + 1, 4): da.delivery_zip_code,
                (offset[i] + 1, 7): da.delivery_country,
                (offset[i] + 2, 3): da.delivery_region,
                (offset[i] + 2, 7): da.delivery_city,
                (offset[i] + 3, 1): da.delivery_street,
                (offset[i] + 3, 5): da.delivery_building,
                (offset[i] + 3, 7): da.delivery_block,
                (offset[i] + 4, 3): da.delivery_contact_name,
                (offset[i] + 4, 7): da.delivery_tel,
                (offset[i] + 5, 7): da.delivery_fax,
                (offset[i] + 6, 5): da.delivery_email,

                (offset[i] + 10, 4): da.warehouse_working_hours_from,
                (offset[i] + 10, 6): da.warehouse_working_hours_to,
                (offset[i] + 11, 4): da.warehouse_break_from,
                (offset[i] + 11, 6): da.warehouse_break_to,
                (offset[i] + 13, 2): da.warehouse_comment,
                (offset[i] + 16, 2): da.warehouse_consignee_code,
                (offset[i] + 17, 2): da.warehouse_station_code,
                (offset[i] + 15, 7): da.warehouse_tc,
                (offset[i] + 16, 7): da.warehouse_pl,
                (offset[i] + 17, 7): da.warehouse_gc,
                (offset[i] + 18, 7): da.warehouse_ag,
                (offset[i] + 19, 7): da.warehouse_2r,
            })

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


class ApproveView(StopProposalMixin, DeliveryFormsetMixin, BaseView, ShowCorrectionsMixin, UpdateProcessView):
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


class SeeDataView(DeliveryFormsetMixin, StopProposalMixin, BaseView, UpdateProcessView):
    """
    Вью, просто показывающее данные в Заявке.
    Применяется, например, для случая, когда пользователь должен перенести данные из Заявки в другие системы.
    """
    pass


class ClientSeeDataView(ShowCorrectionsMixin, SeeDataView):

    can_create_corrections = []
    show_corrections = []


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
    delivery_form = DeliveryAddressForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_show_approving_data_checkbox'] = True
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        delivery_formset = self.get_delivery_formset(request.POST)

        if form.is_valid() and delivery_formset.is_valid():
            delivery_formset.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form, *args, **kwargs):
        current_year = datetime.datetime.now().year
        contract_number = 1

        p = self.get_object()
        # last proposal, ordering = ['-created']
        lp = ProposalProcess.objects.filter(contract_date__year=current_year).first()
        if lp and lp.contract_number:
            try:
                contract_number = int(lp.contract_number.split('/')[0]) + 1
            except ValueError:
                pass

        p.contract_number = '{}/{}'.format(contract_number, current_year)
        p.contract_date = datetime.datetime.now()
        p.save()

        super().form_valid(form, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class DownloadClientsContractView(AddDataView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['downloadable_btn_label'] = _('Download contract')
        return context


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


class ShowProposalView(DeliveryFormsetMixin, DetailProcessView):

    template_name = 'main/proposalconfirmation/show_proposal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ShowProposalForm(instance=self.object)
        return context

    # TODO MBPM-33
    # Проверить, могут ли Клиенты и ACS просматривать не свои заявки
    # def get_queryset(self):
    #     """Return the `QuerySet` that will be used to look up the process."""
    #     if self.queryset is None:
    #         return self.flow_class.process_class._default_manager.all()
    #     return self.queryset.all()


@method_decorator(login_required, name='dispatch')
class MichelinProcessListView(ProcessListView):

    list_display = [
        'process_id', 'process_summary', 'proposal_link',
        'created', 'finished', 'active_tasks'
    ]

    def get_show_proposal_link(self, process):
        if type(process) == ProposalProcess:
            proposal_pk = process.pk

        if type(process) == BibServeProcess:
            proposal_pk = process.proposal.pk

        url_name = '{}:show_proposal'.format(self.request.resolver_match.namespace)
        return reverse(url_name, args=[proposal_pk])

    def process_summary(self, process):
        return mark_safe('<a href="{}">{}</a>'.format(
            self.get_show_proposal_link(process),
            process.summary()
        ))
    process_summary.short_description = _('Proposal')

    def proposal_link(self, process):
        return mark_safe('<a href="{}">{}</a>'.format(
            self.get_process_link(process),
            _('Process')
        ))
    proposal_link.short_description = _('Process')

    def get_queryset(self):
        queryset = super().get_queryset()

        is_client = self.request.user.groups.filter(pk=settings.CLIENTS_GROUP_ID).exists()
        is_acs = self.request.user.groups.filter(pk=settings.ACS_GROUP_ID).exists()
        if is_client:
            if queryset.model == ProposalProcess:
                queryset = queryset.filter(client=self.request.user)

            if queryset.model == BibServeProcess:
                queryset = queryset.filter(proposal__client=self.request.user)

        if is_acs:
            queryset = queryset.filter(acs=self.request.user)

        return queryset
