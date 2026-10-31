from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_username", read_only=True, default="System")

    class Meta:
        model = AuditEvent
        fields = ["id", "created_at", "actor_name", "action", "entity_type", "entity_id", "summary", "metadata"]
        read_only_fields = fields
