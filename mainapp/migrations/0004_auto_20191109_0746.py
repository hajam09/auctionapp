# Generated by Django 2.2.5 on 2019-11-09 07:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0003_auto_20191109_0739'),
    ]

    operations = [
        migrations.RenameField(
            model_name='item',
            old_name='iamgeurl',
            new_name='imageurl',
        ),
    ]
