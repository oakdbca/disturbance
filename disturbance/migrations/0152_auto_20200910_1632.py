# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-10 08:32
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0151_auto_20200910_1405'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apiarysitelocation',
            name='apiary_site',
        ),
        migrations.RemoveField(
            model_name='apiarysitelocation',
            name='approval',
        ),
        migrations.RemoveField(
            model_name='apiarysitelocation',
            name='proposal_apiary',
        ),
        migrations.DeleteModel(
            name='ApiarySiteLocation',
        ),
    ]
