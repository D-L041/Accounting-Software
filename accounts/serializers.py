from django.db import transaction
from rest_framework import serializers

from .models import AcademicYear, ClassRoom, School, SchoolMembership, Student


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name", "code", "address", "phone", "email", "currency", "timezone", "is_active", "created_at"]
        read_only_fields = ["id", "created_at", "is_active"]


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "name", "starts_on", "ends_on", "is_current"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError({"ends_on": "Academic year end must not precede its start."})
        return attrs


class ClassRoomSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = ClassRoom
        fields = ["id", "academic_year", "academic_year_name", "name", "stream", "class_teacher", "is_active"]
        read_only_fields = ["id", "academic_year_name"]

    def validate_academic_year(self, value):
        school = self.context["school"]
        if value.school_id != school.id:
            raise serializers.ValidationError("Academic year must belong to this school.")
        return value


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    classroom_name = serializers.CharField(source="classroom.__str__", read_only=True)

    class Meta:
        model = Student
        fields = [
            "id", "admission_number", "first_name", "middle_name", "last_name", "full_name",
            "date_of_birth", "gender", "guardian_name", "guardian_phone", "guardian_email",
            "admission_date", "classroom", "classroom_name", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "full_name", "classroom_name", "created_at", "updated_at"]

    def validate_classroom(self, value):
        school = self.context["school"]
        if value and value.school_id != school.id:
            raise serializers.ValidationError("Class must belong to this school.")
        return value


class CreateSchoolSerializer(SchoolSerializer):
    class Meta(SchoolSerializer.Meta):
        read_only_fields = ["id", "created_at", "is_active"]

    def create(self, validated_data):
        request = self.context["request"]
        with transaction.atomic():
            school = School.objects.create(**validated_data)
            SchoolMembership.objects.create(school=school, user=request.user, role=SchoolMembership.Role.OWNER)
        return school
