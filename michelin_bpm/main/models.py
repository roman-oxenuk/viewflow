# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as l_
from django.contrib.postgres.fields import JSONField
from viewflow.models import Process


class ProposalProcess(Process):

    class Meta:
        verbose_name = l_('Заявка')
        verbose_name_plural = l_('Заявки')

    country = models.CharField(l_('Страна'), max_length=255)
    city = models.CharField(l_('Город'), max_length=255)
    company_name = models.CharField(l_('Название компании'), max_length=255)
    inn = models.CharField(l_('ИНН'), max_length=255)

    bank_name = models.CharField(l_('Название банка'), max_length=255)
    account_number = models.CharField(l_('Номер расчётного счёта'), max_length=255)

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, db_index=True,
        on_delete=models.CASCADE, verbose_name=l_('Регистрируемый клиент'))

    def get_corrected_fields(self, from_step=None):
        tasks_qs = self.task_set.filter(correction__is_active=True)
        if from_step:
            tasks_qs = tasks_qs.filter(flow_task=from_step)
        corrections = {}
        for task in tasks_qs:
            for corr_obj in task.correction_set.filter(is_active=True):
                for field_name, corr in corr_obj.data.items():
                    if field_name not in corrections:
                        corrections[field_name] = []
                    corrections[field_name].append(corr)
        return corrections


class Correction(models.Model):
    """
    Модель, в которой хранятся данные о том, что должен откорректировать Клиент в своей заявке
    """
    class Meta:
        verbose_name = l_('Корректировка')
        verbose_name_plural = l_('Корректировка')

    task = models.ForeignKey('viewflow.Task', verbose_name=l_('Этап согласования'))
    data = JSONField(l_('Данные о коррекции'))
    is_active = models.BooleanField(l_('Корректировки актуальны?'), default=True, db_index=True)

    created = models.DateTimeField(l_('Дата создания'), auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, db_index=True,
        on_delete=models.CASCADE, verbose_name=l_('Создатель'))
