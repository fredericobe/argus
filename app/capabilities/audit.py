from __future__ import annotations

from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)


class CapabilityAuditLogger:
    def log_event(
        self,
        event: str,
        capability_id: str,
        planner_task: str,
        domains: list[str],
        decision_reason: str,
    ) -> None:
        logger.info(
            "capability_audit=%s",
            json.dumps(
                {
                    "event": event,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "capability_id": capability_id,
                    "planner_task": planner_task,
                    "domains": domains,
                    "decision_reason": decision_reason,
                }
            ),
        )
