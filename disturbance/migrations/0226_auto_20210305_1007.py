# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-03-05 02:07
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0225_auto_20210305_1000'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proposaltypesection',
            name='proposal_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sections', to='disturbance.ProposalType'),
        ),
        migrations.AlterField(
            model_name='sectionquestion',
            name='parent_question',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children_question', to='disturbance.MasterlistQuestion'),
        ),
        migrations.AlterField(
            model_name='sectionquestion',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='question_sections', to='disturbance.MasterlistQuestion'),
        ),
        migrations.AlterField(
            model_name='sectionquestion',
            name='section',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='section_questions', to='disturbance.ProposalTypeSection'),
        ),
    ]
