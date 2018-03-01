# -*- coding: utf-8 -*-
import json
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as l_
from django.dispatch import receiver

import reversion
from reversion.models import Version
from reversion.signals import post_revision_commit
from viewflow.activation import STATUS_CHOICES
from viewflow.models import Process


@reversion.register()
class ProposalProcess(Process):

    class Meta:
        verbose_name = l_('Заявка')
        verbose_name_plural = l_('Заявки')

    OPENING = 0
    CHANGING = 1
    CLOSING = 2

    OPERATION_TYPES = (
        (OPENING, l_('Открытие')),
        (CHANGING, l_('Изменение')),
        (CLOSING, l_('Закрытие')),
    )

    company_name = models.CharField(l_('Название компании'), max_length=255)
    date = models.DateField(l_('Дата'), auto_now_add=True, null=True, blank=True)
    operation_type = models.IntegerField(l_('Формат ОИЗ'), choices=OPERATION_TYPES, default=OPENING)
    jur_form = models.CharField(l_('Статус компании'), max_length=50, null=True, blank=True)
    client_name = models.CharField(l_('Название клиента'), max_length=255, null=True, blank=True)

    jur_address = models.CharField(l_('Юр. Адрес'), max_length=255, null=True, blank=True)
    jur_zip_code = models.CharField(l_('Юр. Индекс'), max_length=50, null=True, blank=True)
    jur_country = models.CharField(l_('Юр. Страна'), max_length=255, null=True, blank=True)
    jur_region = models.CharField(l_('Юр. Регион'), max_length=255, null=True, blank=True)
    jur_city = models.CharField(l_('Юр. Город'), max_length=255, null=True, blank=True)
    jur_street = models.CharField(l_('Юр. Улица'), max_length=255, null=True, blank=True)
    jur_building = models.CharField(l_('Юр. Строение'), max_length=255, null=True, blank=True)
    jur_block = models.CharField(l_('Юр. Корпус'), max_length=255, null=True, blank=True)

    inn = models.CharField(l_('ИНН'), max_length=255, null=True, blank=True)
    kpp = models.CharField(l_('КПП'), max_length=255, null=True, blank=True)
    okpo = models.CharField(l_('ОКПО'), max_length=255, null=True, blank=True)
    ogrn = models.CharField(l_('ОГРН'), max_length=255, null=True, blank=True)

    bank_name = models.CharField(l_('Название банка'), max_length=255, null=True, blank=True)
    bank_details = models.CharField(l_('Информация о банке'), max_length=255, null=True, blank=True)
    account_number = models.CharField(l_('Номер расчётного счёта'), max_length=255, null=True, blank=True)
    bik = models.CharField(l_('Bank identifier code'), max_length=255, null=True, blank=True)
    corr_account_number = models.CharField(l_('Номер корр. счёта'), max_length=255, null=True, blank=True)

    contract_number = models.CharField(l_('Номер договора'), max_length=255, null=True, blank=True)
    contract_date = models.DateField(l_('Дата договора'), max_length=255, null=True, blank=True)

    address = models.CharField(l_('Факт. Адрес'), max_length=255, null=True, blank=True)
    zip_code = models.CharField(l_('Факт. Индекс'), max_length=50, null=True, blank=True)
    country = models.CharField(l_('Факт. Страна'), max_length=255, null=True, blank=True)
    region = models.CharField(l_('Факт. Регион'), max_length=255, null=True, blank=True)
    city = models.CharField(l_('Факт. Город'), max_length=255, null=True, blank=True)
    street = models.CharField(l_('Факт. Улица'), max_length=255, null=True, blank=True)
    building = models.CharField(l_('Факт. Строение'), max_length=255, null=True, blank=True)
    block = models.CharField(l_('Факт. Корпус'), max_length=255, null=True, blank=True)

    dir_name = models.CharField(l_('Директор ФИО'), max_length=255, null=True, blank=True)
    dir_tel = models.CharField(l_('Директор телефон'), max_length=255, null=True, blank=True)
    dir_email = models.CharField(l_('Директор e-mail'), max_length=255, null=True, blank=True)
    dir_fax = models.CharField(l_('Директор fax'), max_length=255, null=True, blank=True)

    buh_name = models.CharField(l_('Бухгалтер ФИО'), max_length=255, null=True, blank=True)
    buh_tel = models.CharField(l_('Бухгалтер телефон'), max_length=255, null=True, blank=True)
    buh_email = models.CharField(l_('Бухгалтер e-mail'), max_length=255, null=True, blank=True)
    buh_fax = models.CharField(l_('Бухгалтер fax'), max_length=255, null=True, blank=True)

    contact_name = models.CharField(l_('Контакт ФИО'), max_length=255, null=True, blank=True)
    contact_tel = models.CharField(l_('Контакт телефон'), max_length=255, null=True, blank=True)
    contact_email = models.CharField(l_('Контакт e-mail'), max_length=255, null=True, blank=True)
    contact_fax = models.CharField(l_('Контакт fax'), max_length=255, null=True, blank=True)

    j_code = models.CharField(l_('J-код'), max_length=255, null=True, blank=True)
    d_code = models.CharField(l_('D-код'), max_length=255, null=True, blank=True)

    is_needs_bibserve_account = models.BooleanField(l_('Is client needs to have a BibServe account?'), default=False)
    bibserve_login = models.CharField(l_('BibServe Login'), max_length=255, null=True, blank=True)
    bibserve_password = models.CharField(l_('BibServe Password'), max_length=255, null=True, blank=True)
    bibserve_email = models.CharField(l_('BibServe email'), max_length=255, null=True, blank=True)
    bibserve_tel = models.CharField(l_('BibServe tel'), max_length=255, null=True, blank=True)

    delivery_client_name = models.CharField(l_('Доставка, Название клиента'), max_length=255, null=True, blank=True)
    delivery_address = models.CharField(l_('Доставка, Адрес'), max_length=255, null=True, blank=True)
    delivery_zip_code = models.CharField(l_('Доставка, Индекс'), max_length=50, null=True, blank=True)
    delivery_country = models.CharField(l_('Доставка, Страна'), max_length=255, null=True, blank=True)
    delivery_region = models.CharField(l_('Доставка, Регион'), max_length=255, null=True, blank=True)
    delivery_city = models.CharField(l_('Доставка, Город'), max_length=255, null=True, blank=True)
    delivery_street = models.CharField(l_('Доставка, Улица'), max_length=255, null=True, blank=True)
    delivery_building = models.CharField(l_('Доставка, Строение'), max_length=255, null=True, blank=True)
    delivery_block = models.CharField(l_('Доставка, Корпус'), max_length=255, null=True, blank=True)
    delivery_contact_name = models.CharField(l_('Доставка, Контактное лицо'), max_length=255, null=True, blank=True)
    delivery_tel = models.CharField(l_('Доставка, телефон'), max_length=255, null=True, blank=True)
    delivery_email = models.CharField(l_('Доставка, e-mail'), max_length=255, null=True, blank=True)
    delivery_fax = models.CharField(l_('Доставка, fax'), max_length=255, null=True, blank=True)

    warehouse_working_days = models.CharField(l_('Дни работы склада'), max_length=255, null=True, blank=True)
    warehouse_working_hours_from = models.CharField(l_('Часы работы склада с'), max_length=255, null=True, blank=True)
    warehouse_working_hours_to = models.CharField(l_('Часы работы склада до'), max_length=255, null=True, blank=True)
    warehouse_break_from = models.CharField(l_('Перерыв c'), max_length=255, null=True, blank=True)
    warehouse_break_to = models.CharField(l_('Перерыв до'), max_length=255, null=True, blank=True)
    warehouse_comment = models.CharField(l_('Комментарии к работе склада'), max_length=255, null=True, blank=True)
    warehouse_consignee_code = models.CharField(l_('Код грузополучателя'), max_length=255, null=True, blank=True)
    warehouse_station_code = models.CharField(l_('Код станции'), max_length=255, null=True, blank=True)
    warehouse_tc = models.IntegerField(l_('TC'), default=0)
    warehouse_pl = models.IntegerField(l_('PL'), default=0)
    warehouse_gc = models.IntegerField(l_('GC'), default=0)
    warehouse_ag = models.IntegerField(l_('GC'), default=0)
    warehouse_2r = models.IntegerField(l_('2R'), default=0)

    acs = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True,
        verbose_name=l_('Менеджер по работе с клиентами'),
        related_name='acs_proposals'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, db_index=True,
        on_delete=models.CASCADE, verbose_name=l_('Регистрируемый клиент'),
        related_name='clients_proposals'
    )

    @property
    def operation_type_name(self):
        """Возвращает название типа операции как строку."""
        return self.OPERATION_TYPES[self.operation_type][1]

    def get_status_display(self):
        return dict(STATUS_CHOICES).get(self.status, self.status)

    def get_corrections_all(self, for_steps):
        """
        TODO MBPM-3:
        Акктуализировать докстринги, а именно переменную for_steps

        Возвращает кверисет всех Корректировок (main.Correction) которые есть для указанной Задачи у текущей Заявки.

        :param for_step: list of string, название шага viewflow.models.Task.flow_task.
                            Строковое имя шага можно получить, использую функцию viewflow.fields.get_task_ref
        :return: queryset of michelin.main.models.Correction
        """
        # {
        #     'for_step': get_task_ref(corr_setting['for_step']),
        #     'made_on': get_task_ref(corr_setting['made_on']) if ('made_on' in corr_setting) else None
        # }
        # corrections_qs = Correction.objects.filter(proposal=self)

        corrections_qs = Correction.objects.none()
        for for_step in for_steps:
            if 'made_on_step' in for_step and for_step['made_on_step']:
                corrections_qs = corrections_qs | Correction.objects.filter(
                    proposal=self,
                    for_step=for_step['for_step'],
                    task__flow_task=for_step['made_on_step']
                ).order_by('-created')
            else:
                corrections_qs = corrections_qs | Correction.objects.filter(
                    proposal=self,
                    for_step=for_step['for_step']
                ).order_by('-created')
        return corrections_qs
        # return Correction.objects.filter(
        #     proposal=self,
        #     for_step__in=for_steps
        # ).order_by('-created')

    def get_correction_active(self, for_step=None):
        """
        TODO MBPM-3:
        Акктуализировать docstring -- возвращает qs с корректировками, которых может быть много
        Возвращает Корректировки (main.Correction), которая сейчас активна для указанной Задачи у текущей Заявки.

        :param for_step: string, название шага viewflow.models.Task.flow_task.
                            Строковое имя шага можно получить, использую функцию viewflow.fields.get_task_ref
        :return: michelin.main.models.Correction
        """
        correction_qs = Correction.objects.filter(proposal=self, is_active=True)
        if for_step:
            correction_qs = correction_qs.filter(for_step=for_step)
        return correction_qs

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
            # ???
            # for_step__in=for_steps
        ).order_by('-created').first()

    def get_last_version(self, for_step=None):
        # TODO MBPM-3:
        # Удалить этот метод? Стрёмный он какой-то.
        # Вместо него можно запрашивать Корректировку, и уже от неё брать версию.
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

    @staticmethod
    def get_diff_fields(current_state, version, fields):
        """
        Возвращает поля, которые различаются с переданной версией.

        :param current_state: dict вида {field_name: field_value}, текущие значения полей Заявки
        :param version: viewflow.models.Version, версия, с которой сравнивается current_state
        :fields: iterable, поля, по которым идёт сравнение
        """
        version_data = json.loads(version.serialized_data)[0]['fields']
        diff_fields = {}
        for field in fields:
            if field in current_state and current_state[field] != version_data[field]:
                diff_fields[field] = {
                    'old_value': version_data[field],
                    'new_value': current_state[field]
                }
        return diff_fields


@reversion.register()
class BibServeProcess(Process):

    class Meta:
        verbose_name = l_('BibServe аккаунт')
        verbose_name_plural = l_('BibServe аккаунты')

    proposal = models.OneToOneField(ProposalProcess, verbose_name=l_('Заявка'))
    login = models.CharField(l_('Login'), max_length=255, null=True, blank=True)
    password = models.CharField(l_('Password'), max_length=255, null=True, blank=True)
    is_allowed_to_activate = models.BooleanField(l_('Is allowed to activate'), default=False)


class Correction(models.Model):
    """
    Модель, в которой хранятся данные о том, что должен откорректировать Клиент в своей заявке.
    По логике приложения, в один момент времени у одной Заявки
    может быть только одна активная Корректировка для одного этапа согласования.
    Чтобы закрепить это утверждение на уровне БД, создан триггер only_one_active_correction_for_proposal_and_task.
    См. main.migrations.0002_add_constraint
    """
    class Meta:
        verbose_name = l_('Корректировка')
        verbose_name_plural = l_('Корректировка')

    proposal = models.ForeignKey(
        ProposalProcess,
        verbose_name=l_('Заявка')
    )
    task = models.ForeignKey(
        'viewflow.Task',
        verbose_name=l_('На каком шаге создана Корректировка'),
    )
    for_step = models.CharField(
        verbose_name=l_('Для какого шага создана Корректировка'),
        max_length=255,
        null=True,
        blank=True,
    )
    reviewed_version = models.ForeignKey(
        'reversion.Version',
        verbose_name=l_('К какой версии заявки относятся корректировки'),
        related_name='corrections_reviewed'
    )
    fixed_in_version = models.ForeignKey(
        'reversion.Version',
        verbose_name=l_('В какой версии корректировки исправленны'),
        related_name='corrections_fixed',
        null=True,
        blank=True,
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


@receiver(post_revision_commit)
def revision_saved(sender, revision, versions, **kwargs):
    """
    Деактивируем объект Корректировки и добавляем к ней информацию о том,
    в какой версии Заявки исправлена Корректировка.
    """
    proposal_versions = [version for version in versions if version._model == ProposalProcess]
    if proposal_versions:
        saved_proposal_version = proposal_versions[0]
        # Для Клиента всегда должна быть одна активная Корретировка, т.к. он общается через Аккаунта,
        # и только Аккаунт может создавать для него Корректировки.
        # А править Заявку может только Клиент.
        # TODO MBPM-3: Закрепить это на уровне констрейта в БД?

        # Если новую версию создал Клиент, то это значит, что он внёс изменения в Заявку и мы можем
        # деактивировать предыдущую Корректировку от Аккаунта
        if saved_proposal_version.object.client == saved_proposal_version.revision.user:
            correction_obj = saved_proposal_version.object.get_correction_active().first()
            if correction_obj:
                correction_obj.is_active = False
                correction_obj.fixed_in_version = saved_proposal_version
                correction_obj.save()
