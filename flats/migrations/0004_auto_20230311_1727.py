# Generated by Django 3.2.15 on 2023-03-11 17:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flats', '0003_residentialcomplex_gallery'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='body',
            field=models.TextField(default='none'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='news',
            name='header',
            field=models.CharField(default='none', max_length=200),
            preserve_default=False,
        ),
    ]
