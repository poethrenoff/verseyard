from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0005_refreshtoken"),
    ]

    operations = [
        migrations.AlterField(
            model_name="poem",
            name="collection",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="poems",
                to="app.collection",
            ),
        ),
    ]
