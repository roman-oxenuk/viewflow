# -*- coding: utf-8 -*-
from django.contrib import admin

from reversion.admin import VersionAdmin

from michelin_bpm.main.models import ProposalProcess


class ProposalProcessAdmin(VersionAdmin):
    pass


admin.site.register(ProposalProcess, ProposalProcessAdmin)
