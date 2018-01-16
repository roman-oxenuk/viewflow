# -*- coding: utf-8 -*-
from viewflow import flow, frontend
from viewflow.base import this, Flow
from django.utils.translation import ugettext_lazy as l_, ugettext as _

from .models import ProposalProcess
from .views import ApproveByAccountManagerView, FixMistakesView, CreateProposalProcessView
from .forms import FixMistakesForm, ApproveByAccountManagerForm
from .nodes import StartNodeView, FixMistakesNodeView, ApproveViewNode, IfNode, SplitNode


def is_approved(activation):
    """
    Возвращает True, если у Заявки нет ни одной активной Корректировки.
    А это значит, что заявка на данном шаге подтверждена и можно переводить её на следующий шаг.

    :param activation: viewflow.activation.Activation
    :return: boolean
    """
    if activation.task.previous.filter(correction__is_active=True).exists():
        return False
    return True


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
        ).Next(this.approve_by_account_manager)
    )

    approve_by_account_manager = (
        ApproveViewNode(
            ApproveByAccountManagerView,
            form_class=ApproveByAccountManagerForm,
            task_description=_('Approve by account manager')
        ).Permission(
            auto_create=True
        ).Next(this.check_approve_by_account_manager)
    )

    check_approve_by_account_manager = (
        IfNode(
            is_approved,
            task_description=_('Check approve by account manager')
        )
        .Then(this.split_flow)
        .Else(this.fix_mistakes_after_account_manager)
    )

    fix_mistakes_after_account_manager = (
        FixMistakesNodeView(
            FixMistakesView,
            form_class=FixMistakesForm,
            mistakes_from_step=this.approve_by_account_manager,
            task_description=_('Fix mistakes after account manager')
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.approve_by_account_manager)
    )

    split_flow = (
        SplitNode(
            task_description=_('Split flow')
        )
        .Next(this.approve_by_credit_manager)
        .Next(this.approve_by_logist)
    )

    approve_by_credit_manager = (
        ApproveViewNode(
            ApproveByAccountManagerView,
            form_class=ApproveByAccountManagerForm,
            task_description=_('Approve by credit manager')
        ).Permission(
            auto_create=True
        ).Next(this.check_approve_by_credit_manager)
    )

    check_approve_by_credit_manager = (
        IfNode(
            is_approved,
            task_description=_('Check approve by credit manager')
        )
        .Then(this.item_prepared)
        .Else(this.fix_mistakes_after_credit_manager)
    )

    fix_mistakes_after_credit_manager = (
        FixMistakesNodeView(
            FixMistakesView,
            form_class=FixMistakesForm,
            mistakes_from_step=this.approve_by_credit_manager,
            task_description=_('Fix mistakes after credit manager')
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.approve_by_credit_manager)
    )

    approve_by_logist = (
        ApproveViewNode(
            ApproveByAccountManagerView,
            form_class=ApproveByAccountManagerForm,
            task_description=_('Approve by logist')
        ).Permission(
            auto_create=True
        ).Next(this.check_approve_by_logist)
    )

    check_approve_by_logist = (
        IfNode(
            is_approved,
            task_description=_('Check approve by logist')
        )
        .Then(this.item_prepared)
        .Else(this.fix_mistakes_after_logist)
    )

    fix_mistakes_after_logist = (
        FixMistakesNodeView(
            FixMistakesView,
            form_class=FixMistakesForm,
            mistakes_from_step=this.approve_by_logist,
            task_description=_('Fix mistakes after logist')
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.approve_by_logist)
    )

    item_prepared = flow.Join(
        task_description=_('Item prepared')
    ).Next(this.end)

    end = flow.End()
