# Generated by Django 3.2.15 on 2023-03-30 16:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flats', '0014_alter_promotion_chessboard_flat'),
    ]

    operations = [
        migrations.AlterField(
            model_name='promotion',
            name='chessboard_flat',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='flats.chessboardflat'),
        ),
    ]
