# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as l_
from django.contrib.postgres.fields import JSONField

from viewflow.models import Process
from reversion.models import Version


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
        on_delete=models.CASCADE, verbose_name=l_('Регистрируемый клиент')
    )

    def get_correction_active(self, for_step):
        """
        Возвращает Корректировку (main.Correction), которая сейчас активна для указанной Задачи у текущей Заявки.

        :param for_step: string, название шага viewflow.models.Task.flow_task.
                            Строковое имя шага можно получить, использую функцию viewflow.fields.get_task_ref
        :return: michelin.main.models.Correction
        """
        return Correction.objects.filter(
            proposal=self,
            task__flow_task=for_step,
            is_active=True
        ).first()

    def get_correction_last(self, for_step):
        """
        Возвращает последнюю Корректировку (main.Correction) для указанной Задачи у текущей Заявки.

        :param for_step: string, название шага viewflow.models.Task.flow_task.
                            Строковое имя шага можно получить, использую функцию viewflow.fields.get_task_ref
        :return: michelin.main.models.Correction
        """
        return Correction.objects.filter(
            proposal=self,
            task__flow_task=for_step,
        ).order_by('-created').first()

    def get_last_version(self, for_step=None):
        """
        Возвращает последнюю Версию (reversion.Version)
        у которой была Корректировка для указанной Задачи у текущей Заявки.

        В рамках пользовательской работы приложения (не через shell или админку) метод никогда не вернёт None,
        т.к. первая версия создаётся сразу после создания Заявки в micehlin_bpm.main.views.CreateProposalProcessView.

        :param for_step: string, название шага viewflow.models.Task.flow_task.
                    Строковое имя шага можно получить, использую функцию viewflow.fields.get_task_ref
        :return: viewflow.models.Version
        """
        if not for_step:
            return Version.objects.get_for_object(self).order_by('-revision__date_created').first()
        else:
            correction_obj = self.get_correction_last(for_step=for_step)
            if correction_obj:
                return correction_obj.reviewed_version

    def get_diff_fields(self, current_state, version, fields):
        """
        Возвращает поля, которые различаются с переданной версией.

        :param current_state: dict вида {field_name: field_value}, текущие значения полей Заявки
        :param version: viewflow.models.Version, версия, с которой сравнивается current_state
        :fields: iterable, поля, по которым идёт сравнение
        """
        diff_fields = {}
        for field in fields:
            if current_state[field] != version.field_dict[field]:
                diff_fields[field] = {
                    'old_value': version.field_dict[field],
                    'new_value': current_state[field]
                }
        return diff_fields


class Correction(models.Model):
    """
    Модель, в которой хранятся данные о том, что должен откорректировать Клиент в своей заявке.
    По логике приложения, в один момент времени у одной Заявки
    может быть только одна активная Корректировка для одного этапа согласования.
    Чтобы закрепить это утверждение на уровне БД, создан триггер only_one_active_correction_for_proposal_and_task.
    См. main.migrations.0004_auto_20180114_1605
    """

    class Meta:
        verbose_name = l_('Корректировка')
        verbose_name_plural = l_('Корректировка')
        unique_together = ('proposal', 'task')      # У одной Задачи может быть
                                                    # только одна Корректировка в рамках одной Заявки.
    proposal = models.ForeignKey(
        ProposalProcess,
        verbose_name=l_('Заявка')
    )
    task = models.ForeignKey(
        'viewflow.Task',
        verbose_name=l_('Этап согласования')
    )
    reviewed_version = models.ForeignKey(
        'reversion.Version',
        verbose_name=l_('К какой версии заявки относятся корректировки')
    )
    data = JSONField(
        l_('Данные о коррекции')
    )
    is_active = models.BooleanField(
        l_('Корректировки актуальны?'),
        default=True,
        db_index=True
    )
    created = models.DateTimeField(
        l_('Дата создания'),
        auto_now_add=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        db_index=True,
        on_delete=models.CASCADE,
        verbose_name=l_('Создатель')
    )
