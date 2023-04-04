# Generated by Django 3.2.15 on 2023-04-01 14:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flats', '0017_auto_20230401_0026'),
    ]

    operations = [
        migrations.AddField(
            model_name='chessboardflat',
            name='called_off',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='chessboardflat',
            name='rejection_reason',
            field=models.CharField(choices=[('incorrect-price', 'Некоректна ціна'), ('incorrect-photo', 'Некоректне фото'), ('incorrect-description', 'Некоректний опис')], max_length=25, null=True),
        ),
    ]
