# Generated by Django 3.2.15 on 2023-03-14 17:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flats', '0004_auto_20230311_1727'),
    ]

    operations = [
        migrations.AddField(
            model_name='corps',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default='2023-01-01'),
            preserve_default=False,
        ),
    ]
