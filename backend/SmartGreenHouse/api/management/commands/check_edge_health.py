from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import EdgeNode


class Command(BaseCommand):
    help = (
        "Mark edge nodes offline when their heartbeat has exceeded the "
        "configured timeout. Run this periodically via an external scheduler."
    )

    def handle(self, *args, **options):
        timeout = getattr(settings, "EDGE_HEARTBEAT_TIMEOUT", 60)
        now = timezone.now()
        threshold = now - timedelta(seconds=timeout)

        online_nodes = list(
            EdgeNode.objects.exclude(
                status=EdgeNode.Status.DISABLED
            ).filter(status=EdgeNode.Status.ONLINE)
        )

        marked_offline = 0
        for node in online_nodes:
            # A missing heartbeat is treated as stale.
            if node.last_heartbeat is None or node.last_heartbeat < threshold:
                node.status = EdgeNode.Status.OFFLINE
                node.save(update_fields=["status", "updated_at"])
                marked_offline += 1
                self.stdout.write(
                    f"Marked node {node.node_id} offline "
                    f"(last_heartbeat={node.last_heartbeat})."
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {len(online_nodes)} online node(s); "
                f"marked {marked_offline} offline."
            )
        )
