# Generated by Django 3.2.15 on 2023-03-27 12:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flats', '0007_alter_photo_sequence_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='chessboard',
            name='number',
        ),
    ]
