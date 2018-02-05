# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as l_, ugettext as _
from django.conf import settings

from viewflow import flow
from viewflow.base import this, Flow
from viewflow.fields import get_task_ref

from michelin_bpm.main.apps import register
from michelin_bpm.main.models import ProposalProcess
from michelin_bpm.main.nodes import StartNodeView, IfNode, SplitNode, SwitchNode, EndNode, ApproveViewNode, ViewNode
from michelin_bpm.main.views import (
    CreateProposalProcessView, ApproveView, FixMistakesView, AddDataView, SeeDataView
)
from michelin_bpm.main.forms import (
    FixMistakesForm, ApproveForm, LogistForm, AddJCodeADVForm, AddBibServerDataForm, SetCreditLimitForm,
    UnblockClientForm, AddACSForm, ActivateBibserveAccountForm, AddDCodeLogistForm
)


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
            task_description=_('Start')
        ).Permission(
            auto_create=True
        ).Next(this.approve_by_account_manager)
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
                {
                    'for_step': this.approve_by_credit_manager,
                    'field_suffix': COMMENT_SUFFIX,
                    'field_label_prefix': l_('Кредитному инспектору уточнение для поля '),
                    'non_field_corr_label': l_('Кредитному инспектору уточнение для всей заявки.'),
                    'is_can_answer_only': True
                },
                {
                    'for_step': this.approve_by_region_chief,
                    'field_suffix': CORR_SUFFIX_2,
                    'field_label_prefix': l_('Шефу региона уточнение для поля '),
                    'non_field_corr_label': l_('Шефу региона уточнение для всей заявки.'),
                    'is_can_answer_only': True
                },
                {
                    'for_step': this.approve_paper_docs,
                    'field_suffix': CORR_SUFFIX_3,
                    'field_label_prefix': l_('Для Sales Admin уточнение для поля '),
                    'non_field_corr_label': l_('Для Sales Admin уточнение для всей заявки.'),
                    'is_can_answer_only': True
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
        ).Next(this.check_approve_by_account_manager)
    )

    check_approve_by_account_manager = (
        SwitchNode(task_description=_('Check approve by account manager'))
        .Case(this.split_flow, lambda a: not has_active_correction(a))
        .Case(
            this.fix_mistakes_after_account_manager,
            lambda a: has_active_correction(a, for_step=this.fix_mistakes_after_account_manager)
        )
        .Case(
            this.split_flow,
            lambda a: (
                has_active_correction(a, for_step=this.approve_by_credit_manager) and
                has_active_correction(a, for_step=this.approve_by_region_chief)
            )
        )
        .Case(
            this.approve_by_credit_manager,
            lambda a: has_active_correction(a, for_step=this.approve_by_credit_manager)
        )
        .Case(
            this.approve_by_region_chief,
            lambda a: has_active_correction(a, for_step=this.approve_by_region_chief)
        )
        .Case(
            this.approve_paper_docs,
            lambda a: has_active_correction(a, for_step=this.approve_paper_docs)
        )
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
        ).Next(this.approve_by_account_manager)
    )

    split_flow = (
        SplitNode(task_description=_('Split flow'))
        .Next(
            this.approve_by_credit_manager,
            cond=lambda a: not is_already_has_task(a, this.approve_by_credit_manager)
        )
        .Next(
            this.approve_by_region_chief,
            cond=lambda a: not is_already_has_task(a, this.approve_by_region_chief)
        )
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
                    'field_suffix': CORR_SUFFIX,
                    'field_label_prefix': l_('Корректировка для поля '),
                    'non_field_corr_label': l_('Корректировка для всей заявки.'),
                }
            ],
            show_corrections=[
                {'for_step': this.approve_by_account_manager, 'made_on_step': this.approve_by_credit_manager},
                {'for_step': this.fix_mistakes_after_account_manager}
            ],
        ).Permission(
            auto_create=True
        ).Next(this.join_credit_manager_and_region_chief)
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
                    'for_step': this.approve_by_account_manager,
                    'field_suffix': CORR_SUFFIX,
                    'field_label_prefix': l_('Корректировка для поля '),
                    'non_field_corr_label': l_('Корректировка для всей заявки.'),
                },
                {
                    'for_step': this.get_comments_from_logist,
                    'field_suffix': COMMENT_SUFFIX,
                    'field_label_prefix': l_('Запросить комментарий у логиста для поля '),
                    'non_field_corr_label': l_('Запрос комментария для всей заявки.'),
                }
            ],
            show_corrections=[
                {'for_step': this.get_comments_from_logist},
                {'for_step': this.approve_by_account_manager, 'made_on_step': this.approve_by_region_chief},
                {'for_step': this.fix_mistakes_after_account_manager}
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
        .Default(this.join_credit_manager_and_region_chief)
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

    join_credit_manager_and_region_chief = flow.Join(
        task_description=_('Join credit manager and region chief')
    ).Next(this.process_to_end_or_account_manager)

    process_to_end_or_account_manager = (
        IfNode(
            lambda a: not has_active_correction(a),
            task_description=_('Process to end or account manager')
        )
        .Then(this.add_j_code_by_adv)
        .Else(this.approve_by_account_manager)
    )

    add_j_code_by_adv = (
        ViewNode(
            AddDataView,
            form_class=AddJCodeADVForm,
            task_description=_('Add J-code by ADV'),
            action_title='J-код добавлен',
        ).Permission(
            auto_create=True
        ).Next(this.split_flow_for_adding_d_code_and_bibserve_admin)
    )

    split_flow_for_adding_d_code_and_bibserve_admin = (
        SplitNode(task_description=_('Split flow for ADV and BibServe Admin'))
        .Next(this.add_d_code_by_logist)
        .Next(
            this.add_bibserve_data,
            cond=lambda a: a.process.is_needs_bibserve_account
        )
    )

    add_d_code_by_logist = (
        ViewNode(
            AddDataView,
            form_class=AddDCodeLogistForm,
            task_description=_('Add D-code by Logist'),
            action_title='D-код добавлен',
        ).Permission(
            auto_create=True
        ).Next(this.join_adding_d_code_and_bibserve_data)
    )

    add_bibserve_data = (
        ViewNode(
            AddDataView,
            form_class=AddBibServerDataForm,
            task_description=_('Add BibServe data'),
            action_title='BibServe данные добавлены',
        ).Permission(
            auto_create=True
        ).Next(this.join_adding_d_code_and_bibserve_data)
    )

    join_adding_d_code_and_bibserve_data = flow.Join(
        task_description=_('Join process after adding J-code and conditionally ddding BibServe data')
    ).Next(this.set_credit_limit)

    set_credit_limit = (
        ViewNode(
            SeeDataView,
            form_class=SetCreditLimitForm,
            task_description=_('Set credit limit'),
            action_title='Кредитный лимит установлен',
        ).Permission(
            auto_create=True
        ).Next(this.approve_paper_docs)
    )

    approve_paper_docs = (
        ApproveViewNode(
            ApproveView,
            form_class=ApproveForm,
            task_description=_('Approve paper docs'),
            action_title='Данные в документах совпадают с данными в системе',
            can_create_corrections=[
                {
                    'for_step': this.approve_by_account_manager,
                    'field_suffix': CORR_SUFFIX,
                    'field_label_prefix': l_('Корректировка для поля '),
                    'non_field_corr_label': l_('Корректировка для всей заявки.'),
                }
            ],
            show_corrections=[
                {'for_step': this.approve_by_account_manager, 'made_on_step': this.approve_paper_docs},
                {'for_step': this.fix_mistakes_after_account_manager}
            ],
        )
        .Permission(
            auto_create=True
        )
        .Next(this.check_approve_paper_docs)
    )

    check_approve_paper_docs = (
        IfNode(
            lambda a: not has_active_correction(a),
            task_description=_('Check approve paper docs')
        )
        .Then(this.unblock_client)
        .Else(this.approve_by_account_manager)
    )

    unblock_client = (
        ViewNode(
            SeeDataView,
            form_class=UnblockClientForm,
            task_description=_('Unblock client by ADV'),
            action_title='Клиент разблокирован',
        ).Permission(
            auto_create=True
        ).Next(this.split_flow_for_add_acs_and_bibserve_activation)
    )

    split_flow_for_add_acs_and_bibserve_activation = (
        SplitNode(task_description=_('Split flow for adding ACS and activating BibServe account'))
        .Next(this.add_acs)
        .Next(
            this.activate_bibserve_account,
            cond=lambda a: a.process.is_needs_bibserve_account
        )
    )

    add_acs = (
        ViewNode(
            AddDataView,
            form_class=AddACSForm,
            task_description=_('Adding ACS'),
            action_title='ACS прикреплён',
        ).Permission(
            auto_create=True
        ).Next(this.join_add_acs_and_activate_bibserve_account)
    )

    activate_bibserve_account = (
        ViewNode(
            SeeDataView,
            form_class=ActivateBibserveAccountForm,
            task_description=_('Activating BibServe account'),
            action_title='BibServe аккаунт активирован',
        ).Permission(
            auto_create=True
        ).Next(this.join_add_acs_and_activate_bibserve_account)
    )

    join_add_acs_and_activate_bibserve_account = flow.Join(
        task_description=_('Join process after adding ACS and activating BibServe account')
    ).Next(this.end)

    end = EndNode(
        task_description=_('End')
    )
