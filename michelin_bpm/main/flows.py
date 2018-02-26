# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as l_, ugettext as _
from django.utils.decorators import method_decorator
from django.conf import settings

from viewflow import flow
from viewflow.base import this, Flow
from viewflow.fields import get_task_ref

from michelin_bpm.main.apps import register
from michelin_bpm.main.models import ProposalProcess, BibServeProcess
from michelin_bpm.main.nodes import (
    StartNodeView, IfNode, SplitNode, SwitchNode, EndNode, ApproveViewNode, ViewNode, StartFunctionNode
)
from michelin_bpm.main.views import (
    CreateProposalProcessView, ApproveView, FixMistakesView, AddDataView, SeeDataView, AddJCodeView,
    UnblockClientView, CreateBibServerAccountView, ActivateBibServeAccountView
)
from michelin_bpm.main.forms import (
    FixMistakesForm, ApproveForm, LogistForm, AddJCodeADVForm, CreateBibServerAccountForm, SetCreditLimitForm,
    UnblockClientForm, AddACSForm, ActivateBibserveAccountForm, AddDCodeLogistForm
)
from michelin_bpm.main.signals import client_unblocked


CORR_SUFFIX = settings.CORRECTION_FIELD_SUFFIX
COMMENT_SUFFIX = settings.COMMENT_REQUEST_FIELD_SUFFIX
CORR_SUFFIX_2 = settings.CORRECTION_FIELD_SUFFIX_2
CORR_SUFFIX_3 = settings.CORRECTION_FIELD_SUFFIX_3


def has_active_correction(activation, for_step=None):
    """
    Возвращает True, если у Заявки нет ни одной активной Корректировки.
    А это значит, что заявка на данном шаге подтверждена и можно переводить её на следующий шаг.

    :param activation: viewflow.activation.Activation
    :param for_step: viewflow.ThisObject
    :return: boolean
    """
    task_qs = activation.process.task_set.filter(correction__is_active=True)
    if for_step:
        if not hasattr(for_step, 'flow_class'):
            setattr(for_step, 'flow_class', ProposalConfirmationFlow)
        for_step = get_task_ref(for_step)
        task_qs = task_qs.filter(correction__for_step=for_step)

    if task_qs.exists():
        return True

    return False


def is_already_has_task(activation, task):
    # TODO MBPM-3:
    # Кажется эта функция не используется
    if not hasattr(task, 'flow_class'):
        setattr(task, 'flow_class', ProposalConfirmationFlow)

    return activation.process.task_set.exclude(
        status='DONE'
    ).filter(
        flow_task=get_task_ref(task)
    ).exists()


def is_already_done(activation, task):
    if not hasattr(task, 'flow_class'):
        setattr(task, 'flow_class', ProposalConfirmationFlow)

    return activation.process.task_set.filter(
        flow_task=get_task_ref(task),
        status='DONE'
    ).exists()


@register
class ProposalConfirmationFlow(Flow):

    process_class = ProposalProcess
    process_title = l_('Обработка заявки')
    process_menu_title = 'Все заявки'
    process_client_menu_title = 'Мои заявки'
    summary_template = '"{{ process.company_name }}" {{ process.city }}, {{ process.country }}'

    start = (
        StartNodeView(
            CreateProposalProcessView,
            fields=[
                'country', 'city', 'company_name', 'inn',
                'bank_name', 'account_number', 'is_needs_bibserve_account'
            ],
            task_description=_('Start of proposal approval process')
        ).Permission(
            auto_create=True
        ).Next(this.split_to_sales_admin)
    )

    split_to_sales_admin = (
        SplitNode(task_description=_('Split to Sales Admin'))
        .Next(this.approve_paper_docs)
        .Next(this.split_for_credit_and_account_manager)
    )

    split_for_credit_and_account_manager = (
        SplitNode(task_description=_('Split for credit and Account Manager'))
        .Next(this.approve_by_account_manager)
        .Next(this.approve_by_credit_manager)
    )

    approve_by_account_manager = (
        ApproveViewNode(
            ApproveView,
            form_class=ApproveForm,
            task_description=_('Approve by account manager'),
            task_comments='Аккаунт-менеджер проверяет заявку',
            action_title='Согласовано',
            # TODO MBPM-3:
            # Переименовать can_create_corrections в can_create_messages ?
            can_create_corrections=[
                {
                    'for_step': this.fix_mistakes_after_account_manager,
                    'field_suffix': CORR_SUFFIX,
                    'field_label_prefix': l_('Клиенту корректировка для поля '),
                    'non_field_corr_label': l_('Клиенту корректировка для всей заявки.'),
                },
            ],
            show_corrections=[
                {'for_step': this.fix_mistakes_after_account_manager},
                {'for_step': this.approve_by_credit_manager},
                {'for_step': this.approve_by_region_chief},
                {'for_step': this.approve_paper_docs},
            ],
        ).Permission(
            auto_create=True
        ).Next(this.choose_the_path)
    )

    choose_the_path = (
        SwitchNode(task_description=_('Choose the path'))
        .Case(
            this.fix_mistakes_after_account_manager,
            lambda a: (
                is_already_done(a, task=this.join_credit_and_account_manager) and
                has_active_correction(a, for_step=this.approve_by_credit_manager)
            )
        )
        .Case(
            this.approve_by_credit_manager,
            lambda a: (
                is_already_done(a, task=this.join_credit_and_account_manager) and
                has_active_correction(a, for_step=this.approve_by_credit_manager)
            )
        )
        .Default(this.join_credit_and_account_manager)
    )

    approve_by_credit_manager = (
        ApproveViewNode(
            ApproveView,
            form_class=ApproveForm,
            task_description=_('Approve by credit manager'),
            action_title='Согласовано',
            can_create_corrections=[
                {
                    'for_step': this.approve_by_account_manager,
                    'field_suffix': COMMENT_SUFFIX,
                    'field_label_prefix': l_('Заблокировать заявку из-за этого поля'),
                    'non_field_corr_label': l_('Заблокировать заявку'),
                }
            ],
            show_corrections=[],
        ).Permission(
            auto_create=True
        ).Next(this.join_credit_and_account_manager)
    )

    join_credit_and_account_manager = flow.Join(
        task_description=_('Join credit and account manager')
    ).Next(this.check_approve_by_credit_and_account_manager)

    check_approve_by_credit_and_account_manager = (
        SwitchNode(task_description=_('Check approve by credit and account manager'))
        .Case(
            this.approve_by_account_manager,
            lambda a: has_active_correction(a, for_step=this.approve_by_account_manager)
        )
        .Case(
            this.fix_mistakes_after_account_manager,
            lambda a: has_active_correction(a, for_step=this.fix_mistakes_after_account_manager)
        )
        .Default(this.approve_by_region_chief)
    )

    fix_mistakes_after_account_manager = (
        ApproveViewNode(
            FixMistakesView,
            form_class=FixMistakesForm,
            task_description=_('Fix mistakes after account manager'),
            action_title='Сохранить',
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.end)
    )

    approve_by_region_chief = (
        ApproveViewNode(
            ApproveView,
            form_class=ApproveForm,
            task_description=_('Approve by region chief'),
            task_comments='Шеф региона проверяет заявку',
            action_title='Согласовано',
            can_create_corrections=[
                {
                    'for_step': this.get_comments_from_logist,
                    'field_suffix': COMMENT_SUFFIX,
                    'field_label_prefix': l_('Запросить комментарий у логиста для поля '),
                    'non_field_corr_label': l_('Запрос комментария для всей заявки.'),
                }
            ],
            show_corrections=[
                {'for_step': this.get_comments_from_logist},
            ],
        )
        .Permission(
            auto_create=True
        )
        .Next(this.check_approve_by_region_chief)
    )

    check_approve_by_region_chief = (
        SwitchNode(task_description=_('Check approve by region chief'))
        .Case(
            this.get_comments_from_logist,
            lambda a: has_active_correction(a, for_step=this.get_comments_from_logist)
        )
        .Default(this.approve_by_adv)
    )

    get_comments_from_logist = (
        ApproveViewNode(
            ApproveView,
            form_class=LogistForm,
            task_description=_('Get comments from logist'),
            action_title='Сохранить',
            can_create_corrections=[
                {
                    'for_step': this.approve_by_region_chief,
                    'field_suffix': COMMENT_SUFFIX,
                    'field_label_prefix': l_('Пояснение шефу региона для поля '),
                    'non_field_corr_label': l_('Пояснение шефу региона для всей заявки.'),
                }
            ],
            # TODO MBPM-3: переименовать на
            # additionaly_show_corrections -- дополнительно показываем корректировки с каких шагов
            # И наверное лучше сделать просто списком.
            show_corrections=[
                {'for_step': this.approve_by_region_chief}
            ]
        ).Permission(
            auto_create=True
        ).Next(this.approve_by_region_chief)
    )

    approve_by_adv = (
        ApproveViewNode(
            ApproveView,
            form_class=ApproveForm,
            task_description=_('Approve by ADV'),
            task_comments='ADV согласовывает заявку',
            action_title='Согласовано',
            can_create_corrections=[],
            show_corrections=[],
        ).Permission(
            auto_create=True
        ).Next(this.add_j_code_by_adv)
    )

    add_j_code_by_adv = (
        ViewNode(
            AddJCodeView,
            form_class=AddJCodeADVForm,
            task_description=_('Add J-code by ADV'),
            action_title='J-код добавлен',
        ).Permission(
            auto_create=True
        ).Next(this.add_d_code_by_logist)
    )

    add_d_code_by_logist = (
        ViewNode(
            AddDataView,
            form_class=AddDCodeLogistForm,
            task_description=_('Add D-code by Logist'),
            action_title='D-код добавлен',
        ).Permission(
            auto_create=True
        ).Next(this.set_credit_limit)
    )

    set_credit_limit = (
        ViewNode(
            SeeDataView,
            form_class=SetCreditLimitForm,
            task_description=_('Set credit limit'),
            action_title='Кредитный лимит установлен',
        ).Permission(
            auto_create=True
        ).Next(this.join_from_sales_admin)
    )

    approve_paper_docs = (
        ApproveViewNode(
            ApproveView,
            form_class=ApproveForm,
            task_description=_('Approve paper docs'),
            action_title='Данные в документах совпадают с данными в системе',
            can_create_corrections=[],
            show_corrections=[],
        )
        .Permission(
            auto_create=True
        )
        .Next(this.join_from_sales_admin)
    )

    join_from_sales_admin = (
        flow.Join(task_description=_('Join from sales admin'))
        .Next(this.unblock_client)
    )

    unblock_client = (
        ViewNode(
            UnblockClientView,
            form_class=UnblockClientForm,
            task_description=_('Unblock client by ADV'),
            action_title='Клиент разблокирован',
        ).Permission(
            auto_create=True
        ).Next(this.add_acs)
    )

    add_acs = (
        ViewNode(
            AddDataView,
            form_class=AddACSForm,
            task_description=_('Adding ACS'),
            action_title='ACS прикреплён',
        ).Permission(
            auto_create=True
        ).Next(this.end)
    )

    end = EndNode(
        task_description=_('End of proposal confirmation process')
    )


@register
class BibServeFlow(Flow):

    process_class = BibServeProcess
    process_title = l_('Регистрация BibServe аккаунта')
    process_menu_title = 'Создание BibServe аккаунта'
    process_client_menu_title = 'Создание BibServe аккаунта'
    # TODO MBPM-3
    # Убрать комментарии:
    # summary_template = '"{{ process.company_name }}" {{ process.city }}, {{ process.country }}'

    start = (
        StartFunctionNode(
            this.start_bibserve,
            task_description=_('Start of BibServe account creation proccess')
        )
        .Next(this.create_account)
    )

    create_account = (
        ViewNode(
            CreateBibServerAccountView,
            form_class=CreateBibServerAccountForm,
            task_description=_('Create BibServe account'),
            action_title='BibServe-аккаунт создан',
        ).Permission(
            auto_create=True
        ).Next(this.check_is_allowed_to_activate)
    )

    check_is_allowed_to_activate = (
        IfNode(
            lambda activation: activation.process.is_allowed_to_activate,
            task_description=_('Check is allowed to activate'),
        )
        .Then(this.activate_account)
        .Else(this.wait_for_allowed_to_activate)
    )

    wait_for_allowed_to_activate = (
        flow.Signal(
            client_unblocked, this.client_unblocked_handler,
            sender=UnblockClientView,
            task_loader=this.task_loader,
            allow_skip=True
        ).Next(this.activate_account)
    )

    activate_account = (
        ViewNode(
            ActivateBibServeAccountView,
            form_class=ActivateBibserveAccountForm,
            task_description=_('Activating BibServe account'),
            action_title='BibServe аккаунт активирован',
        ).Permission(
            auto_create=True
        ).Next(this.end)
    )

    end = EndNode(
        task_description=_('End of BibServe account creation process')
    )

    @method_decorator(flow.flow_start_func)
    def start_bibserve(self, activation, proposal):
        activation.prepare()
        activation.process.proposal = proposal
        activation.done()

    @method_decorator(flow.flow_signal)
    def client_unblocked_handler(self, sender, activation, **signal_kwargs):
        activation.prepare()
        activation.done()

    @staticmethod
    def task_loader(flow_task, **kwargs):
        proposal = kwargs['proposal']
        # Проверяем, есть ли у текущей заявки процесс по созданию BibServe-аккаунта
        if hasattr(proposal, 'bibserveprocess'):
            return flow_task.flow_class.task_class._default_manager.filter(
                flow_task=get_task_ref(flow_task),
                process_id=proposal.bibserveprocess.id
            ).first()
