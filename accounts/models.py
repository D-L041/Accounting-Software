from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class School(models.Model):
    name = models.CharField(max_length=180)
    code = models.SlugField(max_length=60, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    currency = models.CharField(max_length=3, default="KES")
    timezone = models.CharField(max_length=64, default="Africa/Nairobi")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SchoolMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "School administrator"
        ACCOUNTANT = "ACCOUNTANT", "Accountant"
        BURSAR = "BURSAR", "Bursar"
        VIEWER = "VIEWER", "Read only"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="school_memberships")
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.VIEWER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "user"], name="unique_school_user_membership"),
        ]

    def __str__(self):
        return f"{self.user} — {self.school} ({self.role})"


class AcademicYear(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_years")
    name = models.CharField(max_length=40)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_on"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_year_name_per_school"),
            models.UniqueConstraint(fields=["school"], condition=Q(is_current=True), name="one_current_academic_year_per_school"),
            models.CheckConstraint(condition=Q(ends_on__gte=models.F("starts_on")), name="academic_year_end_after_start"),
        ]

    def clean(self):
        super().clean()
        if self.ends_on < self.starts_on:
            raise ValidationError({"ends_on": "Academic year end must not precede its start."})

    def __str__(self):
        return f"{self.school.name} — {self.name}"


class ClassRoom(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classrooms")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="classrooms")
    name = models.CharField(max_length=80)
    stream = models.CharField(max_length=40, blank=True)
    class_teacher = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "stream"]
        constraints = [
            models.UniqueConstraint(fields=["school", "academic_year", "name", "stream"], name="unique_class_stream_per_year"),
        ]

    def clean(self):
        super().clean()
        if self.academic_year_id and self.school_id and self.academic_year.school_id != self.school_id:
            raise ValidationError({"academic_year": "Academic year must belong to the same school."})

    def __str__(self):
        return f"{self.name} {self.stream}".strip()


class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        TRANSFERRED = "TRANSFERRED", "Transferred"
        GRADUATED = "GRADUATED", "Graduated"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="students")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.PROTECT, related_name="students", null=True, blank=True)
    admission_number = models.CharField(max_length=40)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    guardian_name = models.CharField(max_length=160, blank=True)
    guardian_phone = models.CharField(max_length=30, blank=True)
    guardian_email = models.EmailField(blank=True)
    admission_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "admission_number"], name="unique_admission_number_per_school"),
        ]
        indexes = [
            models.Index(fields=["school", "status"], name="student_school_status_idx"),
            models.Index(fields=["school", "last_name", "first_name"], name="student_school_name_idx"),
        ]

    def clean(self):
        super().clean()
        if self.classroom_id and self.school_id and self.classroom.school_id != self.school_id:
            raise ValidationError({"classroom": "Student's class must belong to the same school."})

    @property
    def full_name(self):
        return " ".join(part for part in [self.first_name, self.middle_name, self.last_name] if part)

    def __str__(self):
        return f"{self.admission_number} — {self.full_name}"


class OfflineSyncReceipt(models.Model):
    """Idempotency receipt for authenticated, offline-created expense drafts."""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="offline_sync_receipts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offline_sync_receipts")
    idempotency_key = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    expense = models.ForeignKey("expenses.Expense", null=True, blank=True, on_delete=models.SET_NULL, related_name="offline_sync_receipts")
    purchase_order = models.ForeignKey("expenses.PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL, related_name="offline_sync_receipts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "user", "idempotency_key"], name="unique_offline_sync_operation"),
        ]
        indexes = [models.Index(fields=["school", "created_at"], name="offline_sync_school_time_idx")]
