# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-02-08 07:17
from __future__ import unicode_literals

from django.db import migrations
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0285_auto_20220208_1502'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spatialqueryquestion',
            name='answer_option',
            field=smart_selects.db_fields.ChainedManyToManyField(chained_field='question', chained_model_field='option', to='disturbance.QuestionOption'),
        ),
    ]
