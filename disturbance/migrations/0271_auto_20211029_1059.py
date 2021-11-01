# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-10-29 02:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0270_merge_20211029_0941'),
    ]

    operations = [
        migrations.AlterField(
            model_name='masterlistquestion',
            name='answer_type',
            field=models.CharField(choices=[('text', 'Text'), ('radiobuttons', 'Radio button'), ('checkbox', 'Checkbox'), ('number', 'Number'), ('email', 'Email'), ('select', 'Select'), ('multi-select', 'Multi-select'), ('text_area', 'Text area'), ('label', 'Label'), ('declaration', 'Declaration'), ('file', 'File'), ('date', 'Date')], default='text', max_length=40, verbose_name='Answer Type'),
        ),
        migrations.AlterField(
            model_name='proposaltype',
            name='name',
            field=models.CharField(choices=[('Disturbance', 'Disturbance'), ('Powerline Maintenance', 'Powerline Maintenance'), ('Apiary', 'Apiary'), ('Temporary Use', 'Temporary Use'), ('Site Transfer', 'Site Transfer'), ('Prescribed Burning', 'Prescribed Burning')], default='Disturbance', max_length=64, verbose_name='Application name (eg. Disturbance, Apiary)'),
        ),
    ]
