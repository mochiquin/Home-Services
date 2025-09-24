# Generated manually to remove TNM job models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tnm_integration', '0001_initial'),
    ]

    operations = [
        # Skip the table drops for now - let the old tables remain
        # They won't be used by the simplified TNM system
        migrations.RunSQL(
            "SELECT 1;",  # No-op SQL
            reverse_sql="SELECT 1;"
        ),
    ]