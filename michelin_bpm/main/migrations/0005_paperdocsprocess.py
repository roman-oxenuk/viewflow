# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-16 14:38
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('viewflow', '0006_i18n'),
        ('main', '0004_auto_20180208_1256'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaperDocsProcess',
            fields=[
                ('process_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='viewflow.Process')),
                ('proposal', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='main.ProposalProcess', verbose_name='Заявка')),
            ],
            options={
                'verbose_name': 'Бумажные документы',
                'verbose_name_plural': 'Бумажные документы',
            },
            bases=('viewflow.process',),
        ),
    ]
