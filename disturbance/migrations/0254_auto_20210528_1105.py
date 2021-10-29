# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-28 03:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0253_auto_20210414_1106'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='masterlistquestion',
            options={'verbose_name': 'Schema Masterlist Question'},
        ),
        migrations.AlterModelOptions(
            name='proposaltype',
            options={'verbose_name': 'Schema Proposal Type'},
        ),
        migrations.AlterModelOptions(
            name='proposaltypesection',
            options={'verbose_name': 'Schema Proposal Type Section'},
        ),
        migrations.AlterModelOptions(
            name='questionoption',
            options={'verbose_name': 'Schema Question Option'},
        ),
        migrations.AlterModelOptions(
            name='sectionquestion',
            options={'verbose_name': 'Schema Section Question'},
        ),
        migrations.AddField(
            model_name='applicationtype',
            name='searchable',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='proposaltype',
            name='name',
            field=models.CharField(choices=[('Disturbance', 'Disturbance')], default='Disturbance', max_length=64, verbose_name='Application name (eg. Disturbance, Apiary)'),
        ),
    ]
