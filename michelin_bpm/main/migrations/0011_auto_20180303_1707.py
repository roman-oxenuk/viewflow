# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-03 17:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_auto_20180301_0920'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proposalprocess',
            name='bibserve_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='BibServe email'),
        ),
        migrations.AlterField(
            model_name='proposalprocess',
            name='buh_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='Бухгалтер e-mail'),
        ),
        migrations.AlterField(
            model_name='proposalprocess',
            name='client_email',
            field=models.EmailField(max_length=255, verbose_name='Email пользователя'),
        ),
        migrations.AlterField(
            model_name='proposalprocess',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='Контакт e-mail'),
        ),
        migrations.AlterField(
            model_name='proposalprocess',
            name='delivery_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='Доставка, e-mail'),
        ),
        migrations.AlterField(
            model_name='proposalprocess',
            name='dir_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='Директор e-mail'),
        ),
    ]
