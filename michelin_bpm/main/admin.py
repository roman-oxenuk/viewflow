# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as l_

from reversion.admin import VersionAdmin
from viewflow.models import Process, Task
from viewflow.admin import ProcessAdmin, TaskAdmin
from material.frontend.models import Module

from michelin_bpm.main.models import ProposalProcess, Correction, BibServeProcess, PaperDocsProcess


User = get_user_model()


class ModuleAdmin(admin.ModelAdmin):  # noqa D102
    actions = None
    icon = '<i class="material-icons">view_module</i>'
    list_display = ['label', 'installed']
    readonly_fields = ['label']

    def has_add_permission(self, request):
        """Module added automatically during the database migration."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Module deletion is no allowed."""
        return False


class MichelinAdminSite(AdminSite):

    site_header = l_('Michelin Proposal Registration Admin')
    site_title = l_('Michelin Proposal Registration Admin')
    logout_template = 'main/registration/logged_out.html'


admin_site = MichelinAdminSite(name='myadmin')


class CorrectionInline(admin.TabularInline):

    model = Correction
    extra = 0


class ProposalProcessAdmin(VersionAdmin):

    inlines = [
        CorrectionInline,
    ]


class SiteAdmin(admin.ModelAdmin):
    list_display = ('domain', 'name')
    search_fields = ('domain', 'name')


admin_site.register(User, auth_admin.UserAdmin)
admin_site.register(Group, auth_admin.GroupAdmin)

admin_site.register(Process, ProcessAdmin)
admin_site.register(Task, TaskAdmin)

admin_site.register(ProposalProcess, ProposalProcessAdmin)
admin_site.register(Correction)

admin_site.register(Module, ModuleAdmin)

admin_site.register(BibServeProcess)
admin_site.register(PaperDocsProcess)

admin_site.register(Site, SiteAdmin)
