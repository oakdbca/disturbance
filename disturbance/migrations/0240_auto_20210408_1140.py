# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-04-08 03:40
from __future__ import unicode_literals

from django.db import migrations
import django.db.models.deletion
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0239_auto_20210408_1126'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sectionquestion',
            name='parent_question_another',
            field=smart_selects.db_fields.ChainedForeignKey(blank=True, chained_field='section', chained_model_field='question_sections__section', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='parentquestionanother', to='disturbance.MasterlistQuestion'),
        ),
    ]
