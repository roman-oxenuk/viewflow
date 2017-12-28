# -*- coding: utf-8 -*-
from viewflow import flow, frontend
from viewflow.base import this, Flow
from viewflow.flow.views import CreateProcessView, UpdateProcessView
from viewflow.flow.nodes import View

from .models import ProposalProcess
from .views import ApproveByAccountManagerView, FixMistakesView, CreateProposalProcessView
from .forms import FixMistakesForm, ApproveByAccountManagerForm


def is_approved_by_account_manager(activation):
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

    fix_mistakes = (
        flow.View(
            FixMistakesView,
            form_class=FixMistakesForm
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.created_by
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
        flow.If(is_approved_by_account_manager)
        .Then(this.approve_by_credit_manager)
        .Else(this.fix_mistakes)
    )

    approve_by_credit_manager = (
        flow.View(
            UpdateProcessView,
        ).Permission(
            auto_create=True
        ).Next(this.end)
    )

    end = flow.End()
