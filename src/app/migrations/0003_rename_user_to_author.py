from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0002_collection_active_poem_active"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="User",
            new_name="Author",
        ),
        migrations.AlterField(
            model_name="collection",
            name="author",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="collections",
                to="app.Author",
            ),
        ),
        migrations.AlterField(
            model_name="poem",
            name="author",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="poems",
                to="app.Author",
            ),
        ),
    ]
