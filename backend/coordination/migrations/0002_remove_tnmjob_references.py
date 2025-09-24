# Remove TnmJob foreign key references after TNM simplification

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coordination', '0001_initial'),
    ]

    operations = [
        # Skip the SQL migration for now - let the system run without the old columns
        # The old job_id columns will remain in the database but won't be used
        migrations.RunSQL(
            "SELECT 1;",  # No-op SQL
            reverse_sql="SELECT 1;"
        ),
    ]