# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as l_, ugettext as _
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

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
    UnblockClientView, CreateBibServerAccountView, ActivateBibServeAccountView, ClientAddDataView
)
from michelin_bpm.main.forms import (
    FixMistakesForm, ApproveForm, LogistForm, AddJCodeADVForm, CreateBibServerAccountForm, SetCreditLimitForm,
    UnblockClientForm, AddACSForm, ActivateBibserveAccountForm, AddDCodeLogistForm, SendLinkForm
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
                'person_login', 'person_email', 'person_first_name', 'person_last_name',
                'inn', 'mdm_id', 'phone'
            ],
            task_description=_('Start of proposal approval process')
        ).Permission(
            auto_create=True
        ).Next(this.create_user)
    )

    create_user = flow.Handler(
        this.perform_create_user
    ).Next(this.add_data_by_client)

    add_data_by_client = (
        ViewNode(
            ClientAddDataView,
            form_class=AddDCodeLogistForm,
            task_description=_('Client adds data'),
            action_title='D-код добавлен',
        ).Permission(
            auto_create=True
        ).Assign(
            lambda activation: activation.process.client
        ).Next(this.end)
    )

    end = EndNode(
        task_description=_('End of proposal confirmation process')
    )

    def perform_create_user(self, activation, **kwargs):
        User = get_user_model()
        new_user = User(**{
            'username': activation.process.person_login,
            'email': activation.process.person_email,
            'first_name': activation.process.person_first_name,
            'last_name': activation.process.person_last_name,
        })
        new_user.save()

        clients = Group.objects.get(id=settings.CLIENTS_GROUP_ID)
        clients.user_set.add(new_user)

        activation.process.client = new_user
        activation.process.save()

        password_reset_form = SendLinkForm({'email': new_user.email})
        password_reset_form.is_valid()
        password_reset_form.save()


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
