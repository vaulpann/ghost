# Alerts router — all public endpoints removed.
# Alert configs are managed via seed scripts / direct DB access only.
# The alerting SERVICE still runs internally (dispatches Slack/webhooks on analysis completion).

from fastapi import APIRouter

router = APIRouter(tags=["alerts"])
