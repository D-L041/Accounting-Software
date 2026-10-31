from .models import AuditEvent


def record_event(*, school, actor, action, entity_type, entity_id, summary, metadata=None):
    return AuditEvent.objects.create(
        school=school,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        summary=summary[:255],
        metadata=metadata or {},
    )
