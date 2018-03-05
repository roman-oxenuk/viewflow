# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as l_, gettext as _
from django.core.exceptions import ImproperlyConfigured
from django.conf.urls import url
from django.urls import reverse

from viewflow import ThisObject
from viewflow.flow import nodes
from viewflow.activation import STATUS

from michelin_bpm.main.views import ProposalExcelDocumentView, ProposalPdfContractView


class LinkedNodeMixin:
    """
    Передаёт во view ссылку на свой flow node (инстанс viewflow.Node).
    """
    def ready(self):
        super().ready()
        self._view_args['linked_node'] = self


class TranslatedNodeMixin:
    """
    При приведении к строке возвращает переведённое имя
    """
    task_comments = None

    def __init__(self, *args, **kwargs):
        task_comments = kwargs.pop('task_comments', None)
        if task_comments:
            self.task_comments = task_comments
        super().__init__(*args, **kwargs)

    def __str__(self):
        name = super().__str__()
        return str(l_(name.lower().capitalize()))


class StartNodeView(LinkedNodeMixin, TranslatedNodeMixin, nodes.Start):
    pass


class StartFunctionNode(TranslatedNodeMixin, nodes.StartFunction):
    pass


class IfNode(TranslatedNodeMixin, nodes.If):
    pass


class SplitNode(TranslatedNodeMixin, nodes.Split):
    pass


class SwitchNode(TranslatedNodeMixin, nodes.Switch):
    pass


class EndNode(TranslatedNodeMixin, nodes.End):
    pass


class ViewNode(TranslatedNodeMixin, nodes.View):
    pass


class DownloadableViewNode(ViewNode):

    download_view_class = None

    @property
    def download_view(self):
        if not self.download_view_class:
            raise ImproperlyConfigured(_('You have to set "download_view_class" on DownloadableViewNode'))
        return self.download_view_class.as_view()

    def urls(self):
        urls = super().urls()
        urls.append(
            url(r'^(?P<process_pk>\d+)/{}/(?P<task_pk>\d+)/download/$'.format(self.name),
                self.download_view, {'flow_task': self}, name="{}__download".format(self.name)))
        return urls

    def get_task_url(self, task, url_type='guess', namespace='', **kwargs):
        """Handle `assign`, `unassign` and `execute` url_types.

        If url_type is `guess` task check is it can be assigned, unassigned or executed.
        If true, the action would be returned as guess result url.
        """
        user = kwargs.get('user', None)

        # assign
        if url_type in ['assign', 'guess']:
            if task.status == STATUS.NEW and self.can_assign(user, task):
                url_name = '{}:{}__assign'.format(namespace, self.name)
                return reverse(url_name, kwargs={'process_pk': task.process_id, 'task_pk': task.pk})

        # execute
        if url_type in ['execute', 'guess']:
            if task.status == STATUS.ASSIGNED and self.can_execute(user, task):
                url_name = '{}:{}'.format(namespace, self.name)
                return reverse(url_name, kwargs={'process_pk': task.process_id, 'task_pk': task.pk})

        # unassign
        if url_type in ['unassign']:
            if task.status == STATUS.ASSIGNED and self.can_unassign(user, task):
                url_name = '{}:{}__unassign'.format(namespace, self.name)
                return reverse(url_name, kwargs={'process_pk': task.process_id, 'task_pk': task.pk})

        # download
        if url_type in ['download']:
            url_name = '{}:{}__download'.format(namespace, self.name)
            return reverse(url_name, kwargs={'process_pk': task.process_id, 'task_pk': task.pk})

        return super().get_task_url(task, url_type, namespace=namespace, **kwargs)


class DownloadableXLSViewNode(DownloadableViewNode):

    download_view_class = ProposalExcelDocumentView


class DownloadableContractViewNode(DownloadableViewNode):

    download_view_class = ProposalPdfContractView


class ApproveViewNode(LinkedNodeMixin, TranslatedNodeMixin, nodes.View):

    def ready(self):
        super().ready()
        # Добавляем к viewflow.ThisObject flow_class,
        # иначе в будущем при вызове viewflow.fields.get_task_ref(ThisObject) выйдет ошибка.
        if 'show_corrections' in self._view_args:
            value = self._view_args['show_corrections']
            if isinstance(value, list):
                for obj in value:
                    if isinstance(obj['for_step'], ThisObject):
                        obj['for_step'].flow_class = self.flow_class

                    if 'made_on_step' in obj and isinstance(obj['made_on_step'], ThisObject):
                        obj['made_on_step'].flow_class = self.flow_class

        if 'can_create_corrections' in self._view_args:
            value = self._view_args['can_create_corrections']
            if isinstance(value, list):
                for obj in value:
                    if isinstance(obj['for_step'], ThisObject):
                        obj['for_step'].flow_class = self.flow_class
