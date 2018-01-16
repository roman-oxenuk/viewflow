# -*- coding: utf-8 -*-
from viewflow import ThisObject
from viewflow.flow import nodes
from viewflow.fields import get_task_ref
from django.utils.translation import gettext_lazy as l_


class FixMistakesNodeView(nodes.View):
    """
    Если в переменных для view (self._view_args) есть переменная с именем mistakes_from_step,
    то приводит эту переменную из типа ThisObject в формат строки, в котором она храниться в базе.
    Нужно для того, чтобы во потом по этой строке делать выборку в БД.
    """
    def ready(self):
        super().ready()
        if 'mistakes_from_step' in self._view_args:
            value = self._view_args['mistakes_from_step']
            if isinstance(value, ThisObject):
                value.flow_class = self.flow_class
                self._view_args['mistakes_from_step'] = get_task_ref(value)


class LinkedNodeMixin:
    """
    Передаёт во view ссылку на свой flow node (инстанс viewflow.Node).
    """
    def ready(self):
        super().ready()
        self._view_args['linked_node'] = self

    def __str__(self):
        name = super().__str__()
        return str(l_(name.lower().replace(' ', '_')))


class StartNodeView(LinkedNodeMixin, nodes.Start):
    pass


class ApproveViewNode(LinkedNodeMixin, nodes.View):
    pass
