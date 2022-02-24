# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-02-24 06:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0286_spatialqueryquestion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spatialqueryquestion',
            name='answer_mlq',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='question_options', to='disturbance.QuestionOption'),
        ),
        migrations.AlterField(
            model_name='spatialqueryquestion',
            name='no_polygons_assessor',
            field=models.IntegerField(blank=True, default=-1, verbose_name='No. of polygons to process (Assessor)'),
        ),
        migrations.AlterField(
            model_name='spatialqueryquestion',
            name='no_polygons_proponent',
            field=models.IntegerField(blank=True, default=-1, verbose_name='No. of polygons to process (Proponent)'),
        ),
        migrations.AlterField(
            model_name='spatialqueryquestion',
            name='regions',
            field=models.CharField(blank=True, choices=[('All', 'All')], default='All', max_length=40, verbose_name='Regions'),
        ),
        migrations.AlterField(
            model_name='spatialqueryquestion',
            name='value',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
