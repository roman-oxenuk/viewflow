# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-04 21:13
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_auto_20180304_2014'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryAddress',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_client_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Название клиента')),
                ('delivery_address', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Адрес')),
                ('delivery_zip_code', models.CharField(blank=True, max_length=50, null=True, verbose_name='Доставка, Индекс')),
                ('delivery_country', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Страна')),
                ('delivery_region', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Регион')),
                ('delivery_city', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Город')),
                ('delivery_street', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Улица')),
                ('delivery_building', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Строение')),
                ('delivery_block', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Корпус')),
                ('delivery_address_comment', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Комментарии к адресу')),
                ('delivery_contact_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, Контактное лицо')),
                ('delivery_tel', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, телефон')),
                ('delivery_email', models.EmailField(blank=True, max_length=255, null=True, verbose_name='Доставка, e-mail')),
                ('delivery_fax', models.CharField(blank=True, max_length=255, null=True, verbose_name='Доставка, fax')),
                ('warehouse_working_days', models.CharField(blank=True, max_length=255, null=True, verbose_name='Дни работы склада')),
                ('warehouse_working_hours_from', models.CharField(blank=True, max_length=255, null=True, verbose_name='Часы работы склада с')),
                ('warehouse_working_hours_to', models.CharField(blank=True, max_length=255, null=True, verbose_name='Часы работы склада до')),
                ('warehouse_break_from', models.CharField(blank=True, max_length=255, null=True, verbose_name='Перерыв c')),
                ('warehouse_break_to', models.CharField(blank=True, max_length=255, null=True, verbose_name='Перерыв до')),
                ('warehouse_comment', models.CharField(blank=True, max_length=255, null=True, verbose_name='Комментарии к работе склада')),
                ('warehouse_consignee_code', models.CharField(blank=True, max_length=255, null=True, verbose_name='Код грузополучателя')),
                ('warehouse_station_code', models.CharField(blank=True, max_length=255, null=True, verbose_name='Код станции')),
                ('warehouse_tc', models.IntegerField(blank=True, null=True, verbose_name='TC')),
                ('warehouse_pl', models.IntegerField(blank=True, null=True, verbose_name='PL')),
                ('warehouse_gc', models.IntegerField(blank=True, null=True, verbose_name='GC')),
                ('warehouse_ag', models.IntegerField(blank=True, null=True, verbose_name='GC')),
                ('warehouse_2r', models.IntegerField(blank=True, null=True, verbose_name='2R')),
            ],
            options={
                'verbose_name': 'Доставочный адрес',
                'verbose_name_plural': 'Доставочные адреса',
            },
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_address',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_address_comment',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_block',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_building',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_city',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_client_name',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_contact_name',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_country',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_email',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_fax',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_region',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_street',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_tel',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='delivery_zip_code',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_2r',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_ag',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_break_from',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_break_to',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_comment',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_consignee_code',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_gc',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_pl',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_station_code',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_tc',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_working_days',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_working_hours_from',
        ),
        migrations.RemoveField(
            model_name='proposalprocess',
            name='warehouse_working_hours_to',
        ),
        migrations.AddField(
            model_name='deliveryaddress',
            name='proposal',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.ProposalProcess'),
        ),
    ]
