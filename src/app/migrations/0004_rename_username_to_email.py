from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0003_rename_user_to_author"),
    ]

    operations = [
        migrations.RenameField(
            model_name="author",
            old_name="username",
            new_name="email",
        ),
    ]
