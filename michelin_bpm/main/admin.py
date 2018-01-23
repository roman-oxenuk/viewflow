# -*- coding: utf-8 -*-
from django.contrib import admin

from reversion.admin import VersionAdmin

from michelin_bpm.main.models import ProposalProcess, Correction


class CorrectionInline(admin.TabularInline):

    model = Correction
    extra = 0


class ProposalProcessAdmin(VersionAdmin):

    inlines = [
        CorrectionInline,
    ]


admin.site.register(ProposalProcess, ProposalProcessAdmin)
admin.site.register(Correction)
