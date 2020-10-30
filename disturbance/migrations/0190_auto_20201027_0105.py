# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-10-26 17:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0189_proposalapiary_transferee_email_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarychecklistanswer',
            name='site',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='disturbance.ApiarySiteOnProposal'),
        ),
        migrations.AlterField(
            model_name='apiarychecklistquestion',
            name='checklist_type',
            field=models.CharField(choices=[('apiary', 'Apiary'), ('apiary_per_site', 'Apiary per site'), ('site_transfer', 'Site Transfer')], max_length=30, verbose_name='Checklist Type'),
        ),
    ]
