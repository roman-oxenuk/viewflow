# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as l_, ugettext as _
from django.conf import settings

from viewflow import flow, frontend
from viewflow.base import this, Flow
from viewflow.fields import get_task_ref
from viewflow.models import Process

from michelin_bpm.main.models import ProposalProcess
from michelin_bpm.main.nodes import StartNodeView, IfNode, SwitchNode, EndNode, ApproveViewNode
from michelin_bpm.main.views import CreateProposalProcessView, ApproveView, FixMistakesView
from michelin_bpm.main.forms import FixMistakesForm, ApproveForm, LogistForm


CORR_SUFFIX = settings.CORRECTION_FIELD_SUFFIX
COMMENT_SUFFIX = settings.COMMENT_REQUEST_FIELD_SUFFIX


def has_active_correction(activation, for_step=None):
    """
    Возвращает True, если у Заявки нет ни одной активной Корректировки.
    А это значит, что заявка на данном шаге подтверждена и можно переводить её на следующий шаг.

    :param activation: viewflow.activation.Activation
    :param for_step: viewflow.ThisObject
    :return: boolean
    """
    task_qs = activation.task.previous.filter(correction__is_active=True)
    if for_step:
        if not hasattr(for_step, 'flow_class'):
            setattr(for_step, 'flow_class', ProposalConfirmationFlow)
            for_step = get_task_ref(for_step)
        task_qs = task_qs.filter(correction__for_step=for_step)

    if task_qs.exists():
        return True

    return False


@frontend.register
class ProposalConfirmationFlow(Flow):

    process_class = ProposalProcess

    process_title = l_('Обработка заявки')
    summary_template = "{{ flow_class.process_title }} - {{ process.get_status_display }}"

    start = (
        StartNodeView(
            CreateProposalProcessView,
            fields=[
                'country', 'city', 'company_name', 'inn',
                'bank_name', 'account_number',
            ],
            task_description=_('Start')
        ).Permission(
            auto_create=True
        # ).Next(this.approve_by_account_manager)
        ).Next(this.approve_by_region_chief)
    )

    # approve_by_account_manager = (
        # ApproveViewNode(
        #     ApproveView,
        #     form_class=ApproveForm,
        #     task_description=_('Approve by account manager'),
        #     # can_create_corrections = [
        #     #     {
        #     #         'for_step': this.fix_mistakes_after_account_manager,
        #     #         'field_suffix': CORR_SUFFIX,
        #     #         'field_label_prefix': l_('Корректировка для поля ')
        #     #     }
        #     # ],
        #     # mistakes_for_step=this.fix_mistakes_after_account_manager
        # ).Permission(
        #     auto_create=True
        # ).Next(this.check_approve_by_account_manager)
    # )

    # check_approve_by_account_manager = (
        # IfNode(
        #     # is_approved,
        #     lambda a: not has_active_correction(a),
        #     task_description=_('Check approve by account manager')
        # )
        # # .Then(this.split_flow)
        # .Then(this.end)
        # .Else(this.fix_mistakes_after_account_manager)
    # )

    # fix_mistakes_after_account_manager = (
        # FixMistakesNodeView(
        #     FixMistakesView,
        #     form_class=FixMistakesForm,
        #     mistakes_from_step=this.approve_by_account_manager,
        #     task_description=_('Fix mistakes after account manager')
        # ).Permission(
        #     auto_create=True
        # ).Assign(
        #     lambda activation: activation.process.created_by
        # ).Next(this.approve_by_account_manager)
    # )

    # split_flow = (
        # SplitNode(
        #     task_description=_('Split flow')
        # )
        # .Next(this.approve_by_credit_manager)
        # .Next(this.approve_by_region_chief)
    # )

    # approve_by_credit_manager = (
        # ApproveViewNode(
        #     ApproveView,
        #     form_class=ApproveForm,
        #     task_description=_('Approve by credit manager')
        # ).Permission(
        #     auto_create=True
        # ).Next(this.check_approve_by_credit_manager)
    # )

    # check_approve_by_credit_manager = (
        # IfNode(
        #     is_approved,
        #     task_description=_('Check approve by credit manager')
        # )
        # .Then(this.item_prepared)
        # .Else(this.fix_mistakes_after_credit_manager)
    # )

    # fix_mistakes_after_credit_manager = (
        # FixMistakesNodeView(
        #     FixMistakesView,
        #     form_class=FixMistakesForm,
        #     mistakes_from_step=this.approve_by_credit_manager,
        #     task_description=_('Fix mistakes after credit manager')
        # ).Permission(
        #     auto_create=True
        # ).Assign(
        #     lambda activation: activation.process.created_by
        # ).Next(this.approve_by_credit_manager)
    # )

    approve_by_region_chief = (
        ApproveViewNode(
            ApproveView,
            form_class=ApproveForm,
            task_description=_('Approve by region chief'),
            can_create_corrections = [
                {
                    'for_step': this.fix_mistakes_after_region_chief,
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
            show_corrections = [
                {
                    'for_step': this.get_comments_from_logist,
                },
                {
                    'for_step': this.fix_mistakes_after_region_chief
                }
            ],
        )
        .Permission(
            auto_create=True
        )
        .Next(this.check_approve_by_region_chief)
    )

    check_approve_by_region_chief = (
        SwitchNode(
            task_description=_('Check approve by region hief'),
        )
        .Case(this.end, lambda a: not has_active_correction(a))
        .Case(
            this.get_comments_from_logist,
            lambda a: has_active_correction(a, for_step=this.get_comments_from_logist)
        )
        .Case(
            this.fix_mistakes_after_region_chief,
            lambda a: has_active_correction(a, for_step=this.fix_mistakes_after_region_chief)
        )
    )

    fix_mistakes_after_region_chief = (
        ApproveViewNode(
            FixMistakesView,
            form_class=FixMistakesForm,
            task_description=_('Fix mistakes after region chief')
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.approve_by_region_chief)
    )

    get_comments_from_logist = (
        ApproveViewNode(
            ApproveView,
            form_class=LogistForm,
            task_description=_('Get comments from logist'),
            can_create_corrections = [
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
            show_corrections = [
                {
                    'for_step': this.approve_by_region_chief
                }
            ]
        ).Permission(
            auto_create=True
        ).Next(this.approve_by_region_chief)
    )

    item_prepared = flow.Join(
        task_description=_('Item prepared')
    ).Next(this.end)

    end = EndNode(
        task_description=_('End')
    )
