# -*- coding: utf-8 -*-
from django.template.loader import get_template
from django.template import Template, TemplateDoesNotExist
from viewflow.frontend.apps import ViewflowFrontendConfig


default_app_config = 'michelin_bpm.main.apps.MichelinBPMFrontendConfig'  # NOQA


class MichelinBPMFrontendConfig(ViewflowFrontendConfig):

    name = 'michelin_bpm.main.apps'
    label = 'michelin_viewflow_frontend'

    def menu(self):
        try:
            return get_template('main/menu.html')
        except TemplateDoesNotExist:
            return Template('')

    def base_template(self):
        return get_template('main/base_module.html')

    def register(self, flow_class, viewset_class=None):
        """Register a flow class at the frontend."""
        from .viewset import MichelinFlowViewSet

        if flow_class not in self._registry:
            if viewset_class is None:
                viewset_class = MichelinFlowViewSet

            self._registry[flow_class] = viewset_class(flow_class=flow_class)


def register(flow_class, viewset_class=None):
    from django.apps import apps
    apps.get_app_config('michelin_viewflow_frontend').register(flow_class, viewset_class=viewset_class)
    return flow_class
