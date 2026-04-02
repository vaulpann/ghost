"""Alert dispatch service — sends notifications via Slack/webhook when analysis finds threats."""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import AlertConfig, AlertHistory, AlertStatus, ChannelType
from app.models.analysis import Analysis, RiskLevel
from app.models.package import Package
from app.models.version import Version

logger = logging.getLogger(__name__)

RISK_LEVEL_ORDER = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}

RISK_LEVEL_FROM_STR = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

RISK_EMOJIS = {
    RiskLevel.NONE: "",
    RiskLevel.LOW: ":large_yellow_circle:",
    RiskLevel.MEDIUM: ":warning:",
    RiskLevel.HIGH: ":red_circle:",
    RiskLevel.CRITICAL: ":rotating_light:",
}


async def dispatch_alerts(db: AsyncSession, analysis: Analysis) -> int:
    """Check all alert configs and send notifications for this analysis.
    Returns the number of alerts sent.
    """
    if not analysis.risk_level:
        return 0

    # Load related data
    result = await db.execute(select(Version).where(Version.id == analysis.version_id))
    version = result.scalar_one()

    result = await db.execute(select(Package).where(Package.id == version.package_id))
    package = result.scalar_one()

    # Get all enabled alert configs
    result = await db.execute(
        select(AlertConfig).where(AlertConfig.enabled == True)  # noqa: E712
    )
    configs = result.scalars().all()

    sent_count = 0
    for config in configs:
        # Check risk level threshold
        config_level = RISK_LEVEL_FROM_STR.get(config.min_risk_level, 3)
        analysis_level = RISK_LEVEL_ORDER.get(analysis.risk_level, 0)
        if analysis_level < config_level:
            continue

        # Check registry filter
        if config.registries and package.registry not in config.registries:
            continue

        # Check package filter
        if config.packages and str(package.id) not in config.packages:
            continue

        # Send the alert
        try:
            if config.channel_type == ChannelType.SLACK:
                await _send_slack_alert(config, package, version, analysis)
            elif config.channel_type == ChannelType.WEBHOOK:
                await _send_webhook_alert(config, package, version, analysis)

            # Record success
            history = AlertHistory(
                alert_config_id=config.id,
                analysis_id=analysis.id,
                status=AlertStatus.SENT,
            )
            db.add(history)
            sent_count += 1

        except Exception as e:
            logger.error("Failed to send alert %s: %s", config.name, e)
            history = AlertHistory(
                alert_config_id=config.id,
                analysis_id=analysis.id,
                status=AlertStatus.FAILED,
                response_data={"error": str(e)},
            )
            db.add(history)

    await db.commit()
    return sent_count


async def _send_slack_alert(
    config: AlertConfig,
    package: Package,
    version: Version,
    analysis: Analysis,
) -> None:
    webhook_url = config.channel_config.get("webhook_url") or settings.slack_webhook_url
    if not webhook_url:
        raise ValueError("No Slack webhook URL configured")

    emoji = RISK_EMOJIS.get(analysis.risk_level, "")
    risk_text = f"{analysis.risk_level.upper()}" if analysis.risk_level else "UNKNOWN"
    dashboard_url = f"{settings.frontend_url}/analyses/{analysis.id}"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Ghost Alert: {package.name}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Package:*\n{package.name}"},
                {"type": "mrkdwn", "text": f"*Registry:*\n{package.registry}"},
                {"type": "mrkdwn", "text": f"*Version:*\n{version.previous_version_string} → {version.version_string}"},
                {"type": "mrkdwn", "text": f"*Risk:*\n{risk_text} ({analysis.risk_score:.1f}/10)"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary:*\n{analysis.summary or 'No summary available'}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Analysis"},
                    "url": dashboard_url,
                    "style": "danger" if analysis.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) else "primary",
                }
            ],
        },
    ]

    async with httpx.AsyncClient() as client:
        resp = await client.post(webhook_url, json={"blocks": blocks})
        resp.raise_for_status()


async def _send_webhook_alert(
    config: AlertConfig,
    package: Package,
    version: Version,
    analysis: Analysis,
) -> None:
    webhook_url = config.channel_config.get("url")
    if not webhook_url:
        raise ValueError("No webhook URL configured")

    payload = {
        "event": "ghost.analysis.complete",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "package": {
            "name": package.name,
            "registry": package.registry,
        },
        "version": {
            "from": version.previous_version_string,
            "to": version.version_string,
        },
        "analysis": {
            "id": str(analysis.id),
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level if analysis.risk_level else None,
            "summary": analysis.summary,
            "finding_count": len(analysis.findings) if analysis.findings else 0,
        },
        "dashboard_url": f"{settings.frontend_url}/analyses/{analysis.id}",
    }

    headers = config.channel_config.get("headers", {})
    async with httpx.AsyncClient() as client:
        resp = await client.post(webhook_url, json=payload, headers=headers)
        resp.raise_for_status()
