# Generated by Django 3.2.15 on 2023-03-02 19:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flats', '0002_auto_20230302_1421'),
    ]

    operations = [
        migrations.AddField(
            model_name='residentialcomplex',
            name='gallery',
            field=models.OneToOneField(default=1, on_delete=django.db.models.deletion.PROTECT, to='flats.gallery'),
            preserve_default=False,
        ),
    ]
