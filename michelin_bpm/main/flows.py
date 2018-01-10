# -*- coding: utf-8 -*-
from viewflow import flow, frontend
from viewflow.base import this, Flow
from viewflow.flow.views import CreateProcessView, UpdateProcessView
from viewflow.flow.nodes import View

from .models import ProposalProcess
from .views import ApproveByAccountManagerView, FixMistakesView, CreateProposalProcessView
from .forms import FixMistakesForm, ApproveByAccountManagerForm
from .nodes import FixMistakesNodeView


def is_approved(activation):
    if activation.task.previous.filter(correction__is_active=True).exists():
        return False
    return True


@frontend.register
class ProposalConfirmationFlow(Flow):

    process_class = ProposalProcess

    start = (
        flow.Start(
            CreateProposalProcessView,
            fields=[
                'country', 'city', 'company_name', 'inn',
                'bank_name', 'account_number',
            ]
        ).Permission(
            auto_create=True
        ).Next(this.approve_by_account_manager)
    )

    approve_by_account_manager = (
        flow.View(
            ApproveByAccountManagerView,
            form_class=ApproveByAccountManagerForm
        ).Permission(
            auto_create=True
        ).Next(this.check_approve_by_account_manager)
    )

    check_approve_by_account_manager = (
        flow.If(is_approved)
        .Then(this.split_flow)
        .Else(this.fix_mistakes_after_account_manager)
    )

    fix_mistakes_after_account_manager = (
        FixMistakesNodeView(
            FixMistakesView,
            form_class=FixMistakesForm,
            mistakes_from_step=this.approve_by_account_manager
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.approve_by_account_manager)
    )

    split_flow = (
        flow.Split()
        .Next(this.approve_by_credit_manager)
        .Next(this.approve_by_logist)
    )

    approve_by_credit_manager = (
        flow.View(
            ApproveByAccountManagerView,
            form_class=ApproveByAccountManagerForm
        ).Permission(
            auto_create=True
        ).Next(this.check_approve_by_credit_manager)
    )

    check_approve_by_credit_manager = (
        flow.If(is_approved)
        .Then(this.item_prepared)
        .Else(this.fix_mistakes_after_credit_manager)
    )

    fix_mistakes_after_credit_manager = (
        FixMistakesNodeView(
            FixMistakesView,
            form_class=FixMistakesForm,
            mistakes_from_step=this.approve_by_credit_manager
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.approve_by_credit_manager)
    )

    approve_by_logist = (
        flow.View(
            ApproveByAccountManagerView,
            form_class=ApproveByAccountManagerForm
        ).Permission(
            auto_create=True
        ).Next(this.check_approve_by_logist)
    )

    check_approve_by_logist = (
        flow.If(is_approved)
        .Then(this.item_prepared)
        .Else(this.fix_mistakes_after_logist)
    )

    fix_mistakes_after_logist = (
        FixMistakesNodeView(
            FixMistakesView,
            form_class=FixMistakesForm,
            mistakes_from_step=this.approve_by_logist
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
        ).Next(this.approve_by_logist)
    )

    item_prepared = flow.Join().Next(this.end)

    end = flow.End()
