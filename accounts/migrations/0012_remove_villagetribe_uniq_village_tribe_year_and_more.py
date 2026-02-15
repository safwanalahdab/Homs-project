from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_remove_villagetribe_uniq_village_tribe_year_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE accounts_villagetribe DROP CONSTRAINT IF EXISTS uniq_village_tribe_year;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE accounts_villagetribe DROP CONSTRAINT IF EXISTS uniq_village_tribe;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="villagetribe",
                    name="uniq_village_tribe_year",
                ),
                migrations.RemoveConstraint(
                    model_name="villagetribe",
                    name="uniq_village_tribe",
                ),
            ],
        ),
    ]
