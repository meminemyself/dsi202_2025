# Generated by Django 5.1.6 on 2025-04-30 05:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0006_tree_average_rating_tree_review_count_tree_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
