# Generated by Django 3.2.15 on 2023-03-27 12:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flats', '0009_remove_chessboard_chess_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='chessboard',
            name='residential_complex',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='flats.residentialcomplex'),
            preserve_default=False,
        ),
    ]