# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-10 06:05
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0150_auto_20200910_1125'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='apiarysitelocation',
            options={'ordering': ['-modified_at', '-created_at']},
        ),
        migrations.AlterUniqueTogether(
            name='apiarysiteonapproval',
            unique_together=set([('apiary_site', 'approval')]),
        ),
        migrations.AlterUniqueTogether(
            name='apiarysiteonproposal',
            unique_together=set([('apiary_site', 'proposal_apiary')]),
        ),
    ]
