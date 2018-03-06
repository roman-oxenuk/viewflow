# -*- coding: utf-8 -*-
from django import dispatch
from django.conf import settings
from django.template import loader
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import Permission, Group
from django.contrib.sites.models import Site
from django.utils.translation import ugettext as _
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives

from viewflow.signals import flow_finished
from viewflow.models import Task

from michelin_bpm.main.views import UnblockClientView
from michelin_bpm.main.utils import AgoraMailerClient


client_unblocked = dispatch.Signal(providing_args=['proposal'])


@receiver(client_unblocked, sender=UnblockClientView)
def client_unblocked_handler(sender, proposal, **kwargs):
    # Проверяем, есть ли у текущей заявки процесс по созданию BibServe-аккаунта
    if hasattr(proposal, 'bibserveprocess'):
        proposal.bibserveprocess.is_allowed_to_activate = True
        proposal.bibserveprocess.save()


@receiver(post_save, sender=Task)
def task_created(sender, instance, created, **kwargs):
    EMAIL_ON_TASK_STARTED = [
        'approve_by_account_manager',
        'approve_by_credit_manager',
        'fix_mistakes_after_account_manager',
        'approve_by_region_chief',
        'get_comments_from_logist',
        'approve_by_adv',
        'create_user_in_inner_systems',
        'add_j_code_by_adv',
        'add_d_code_by_logist',
        'set_credit_limit',
        'approve_paper_docs',
        'unblock_client',
        'add_acs',
    ]
    if created and instance.flow_task.name in EMAIL_ON_TASK_STARTED:
        perm_name = 'can_{}_{}'.format(
            instance.flow_task.name,
            instance.flow_process.flow_class.process_class._meta.model_name,
        )
        perm = Permission.objects.filter(codename=perm_name).first()
        if perm:
            subject = _('New task: ')
            subject += instance.flow_task.task_title

            if not settings.DEBUG:
                current_site = Site.objects.get_current()
                domain = current_site.domain
                protocol = 'https'
            else:
                domain = 'localhost:8000'
                protocol = 'http'
            task_link = instance.flow_task.get_task_url(
                task=instance,
                namespace='viewflow:main:proposalconfirmation'
            )
            task_link += '?back=%2Fworkflow%2F'
            context = {
                'task_title': instance.flow_task.task_title,
                'task_created': instance.created,
                'proposal_name': instance.flow_process.summary(),
                'task_link': task_link,
                'domain': domain,
                'protocol': protocol,
            }
            from_email = settings.DEFAULT_FROM_EMAIL

            for group in perm.group_set.all():
                for user in group.user_set.filter(is_active=True):
                    if settings.DEBUG:
                        body = loader.render_to_string(
                            'main/proposalconfirmation/email/new_task_created.html',
                            context
                        )
                        email_message = EmailMultiAlternatives(subject, body, from_email, [user.email])
                        email_message.send()
                    else:
                        mailer = AgoraMailerClient()
                        mailer.send('michelin_bpm_new_task_created', user.email, from_email, context)


@receiver(flow_finished)
def new_account_created(sender, process, task, **kwargs):
    from michelin_bpm.main.flows import ProposalConfirmationFlow
    if sender == ProposalConfirmationFlow:
        subject = _('New account created for proposal: ')
        subject += process.summary()

        if not settings.DEBUG:
            current_site = Site.objects.get_current()
            domain = current_site.domain
            protocol = 'https'
        else:
            domain = 'localhost:8000'
            protocol = 'http'

        task_link = reverse(
            'viewflow:main:proposalconfirmation:show_proposal',
            kwargs={'process_pk': process.id}
        )

        context = {
            'proposal_name': process.summary(),
            'process_finished': process.finished,
            'task_link': task_link,
            'acs_first_name': process.acs.first_name,
            'acs_last_name': process.acs.last_name,
            'acs_email': process.acs.email,
            'domain': domain,
            'protocol': protocol,
            'project_name': 'michelin_bpm'
        }
        from_email = settings.DEFAULT_FROM_EMAIL

        rtc_group = Group.objects.get(id=settings.RTC_GROUP_ID)
        send_to_emails = [user.email for user in rtc_group.user_set.all()]
        send_to_emails += [process.client.email]

        for send_to in send_to_emails:
            if settings.DEBUG:
                body = loader.render_to_string(
                    'main/proposalconfirmation/email/new_account_created.html',
                    context
                )
                email_message = EmailMultiAlternatives(subject, body, from_email, [send_to])
                email_message.send()
            else:
                mailer = AgoraMailerClient()
                mailer.send('michelin_bpm_new_account_created', send_to, from_email, context)


@receiver(flow_finished)
def new_bibserve_account_created(sender, process, task, **kwargs):
    from michelin_bpm.main.flows import BibServeFlow
    if sender == BibServeFlow:
        subject = _('BibServe account created for proposal: ')
        subject += process.summary()

        if not settings.DEBUG:
            current_site = Site.objects.get_current()
            domain = current_site.domain
            protocol = 'https'
        else:
            domain = 'localhost:8000'
            protocol = 'http'

        task_link = reverse(
            'viewflow:main:proposalconfirmation:show_proposal',
            kwargs={'process_pk': process.proposal.id}
        )
        context = {
            'proposal_name': process.proposal.summary(),
            'process_finished': process.finished,
            'task_link': task_link,
            'domain': domain,
            'protocol': protocol,
            'bibserve_link': settings.BIBSERVE_LINK,
            'bibserve_login': process.proposal.bibserve_login,
            'bibserve_password': process.proposal.bibserve_password,
            'project_name': 'michelin_bpm'
        }
        from_email = settings.DEFAULT_FROM_EMAIL

        if settings.DEBUG:
            body = loader.render_to_string(
                'main/proposalconfirmation/email/new_bibserve_account_created.html',
                context
            )
            email_message = EmailMultiAlternatives(subject, body, from_email, [process.proposal.client.email])
            email_message.send()
        else:
            mailer = AgoraMailerClient()
            mailer.send('michelin_bpm_new_bibserve_account_created', process.proposal.client.email, from_email, context)
