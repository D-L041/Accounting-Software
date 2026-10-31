import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="School",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("code", models.SlugField(max_length=60, unique=True)),
                ("address", models.TextField(blank=True)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("currency", models.CharField(default="KES", max_length=3)),
                ("timezone", models.CharField(default="Africa/Nairobi", max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SchoolMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("OWNER", "Owner"), ("ADMIN", "School administrator"), ("ACCOUNTANT", "Accountant"), ("BURSAR", "Bursar"), ("VIEWER", "Read only")], default="VIEWER", max_length=12)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="accounts.school")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="school_memberships", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AcademicYear",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=40)),
                ("starts_on", models.DateField()),
                ("ends_on", models.DateField()),
                ("is_current", models.BooleanField(default=False)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="academic_years", to="accounts.school")),
            ],
            options={"ordering": ["-starts_on"]},
        ),
        migrations.CreateModel(
            name="ClassRoom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("stream", models.CharField(blank=True, max_length=40)),
                ("class_teacher", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="classrooms", to="accounts.academicyear")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classrooms", to="accounts.school")),
            ],
            options={"ordering": ["name", "stream"]},
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("admission_number", models.CharField(max_length=40)),
                ("first_name", models.CharField(max_length=80)),
                ("middle_name", models.CharField(blank=True, max_length=80)),
                ("last_name", models.CharField(max_length=80)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("gender", models.CharField(blank=True, max_length=20)),
                ("guardian_name", models.CharField(blank=True, max_length=160)),
                ("guardian_phone", models.CharField(blank=True, max_length=30)),
                ("guardian_email", models.EmailField(blank=True, max_length=254)),
                ("admission_date", models.DateField()),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive"), ("TRANSFERRED", "Transferred"), ("GRADUATED", "Graduated")], default="ACTIVE", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("classroom", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="students", to="accounts.classroom")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="students", to="accounts.school")),
            ],
            options={"ordering": ["last_name", "first_name"]},
        ),
        migrations.AddConstraint(
            model_name="schoolmembership",
            constraint=models.UniqueConstraint(fields=("school", "user"), name="unique_school_user_membership"),
        ),
        migrations.AddConstraint(
            model_name="academicyear",
            constraint=models.UniqueConstraint(fields=("school", "name"), name="unique_academic_year_name_per_school"),
        ),
        migrations.AddConstraint(
            model_name="academicyear",
            constraint=models.CheckConstraint(condition=models.Q(("ends_on__gte", models.F("starts_on"))), name="academic_year_end_after_start"),
        ),
        migrations.AddConstraint(
            model_name="classroom",
            constraint=models.UniqueConstraint(fields=("school", "academic_year", "name", "stream"), name="unique_class_stream_per_year"),
        ),
        migrations.AddConstraint(
            model_name="student",
            constraint=models.UniqueConstraint(fields=("school", "admission_number"), name="unique_admission_number_per_school"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["school", "status"], name="student_school_status_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["school", "last_name", "first_name"], name="student_school_name_idx"),
        ),
    ]
