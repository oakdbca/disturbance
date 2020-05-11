# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-05-11 07:12
from __future__ import unicode_literals

import disturbance.components.compliances.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0029_auto_20200508_1238'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteApplicationFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=8)),
                ('date_of_enforcement', models.DateField(blank=True, null=True)),
            ],
            options={
                'ordering': ('date_of_enforcement',),
            },
        ),
        migrations.CreateModel(
            name='SiteCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=200)),
            ],
        ),
        migrations.AlterField(
            model_name='compliancedocument',
            name='_file',
            field=models.FileField(max_length=500, upload_to=disturbance.components.compliances.models.update_proposal_complaince_filename),
        ),
        migrations.AddField(
            model_name='siteapplicationfee',
            name='site_category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='site_application_fees', to='disturbance.SiteCategory'),
        ),
    ]
