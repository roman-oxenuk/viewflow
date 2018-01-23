# -*- coding: utf-8 -*-
from viewflow import ThisObject
from viewflow.flow import nodes
from viewflow.fields import get_task_ref
from django.utils.translation import gettext_lazy as l_


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
    def __str__(self):
        name = super().__str__()
        return str(l_(name.lower().capitalize()))


class StartNodeView(LinkedNodeMixin, TranslatedNodeMixin, nodes.Start):
    pass


class IfNode(TranslatedNodeMixin, nodes.If):
    pass


class SplitNode(TranslatedNodeMixin, nodes.Split):
    pass


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

        if 'can_create_corrections' in self._view_args:
            value = self._view_args['can_create_corrections']
            if isinstance(value, list):
                for obj in value:
                    if isinstance(obj['for_step'], ThisObject):
                        obj['for_step'].flow_class = self.flow_class
