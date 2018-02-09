# -*- coding: utf-8 -*-
from django import dispatch
from django.dispatch import receiver

from michelin_bpm.main.views import UnblockClientView


client_unblocked = dispatch.Signal(providing_args=['proposal'])


@receiver(client_unblocked, sender=UnblockClientView)
def client_unblocked_handler(sender, proposal, **kwargs):
    # Проверяем, есть ли у текущей заявки процесс по созданию BibServe-аккаунта
    if hasattr(proposal, 'bibserveprocess'):
        proposal.bibserveprocess.is_allowed_to_activate = True
        proposal.bibserveprocess.save()
