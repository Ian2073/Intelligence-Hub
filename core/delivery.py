from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from connectors.telegram import TelegramClient, TelegramNotification
from core.intelligence_brief import IntelligenceBrief


@dataclass(frozen=True)
class DeliveryStatus:
    channel: str
    status: str
    detail: str


def failed_delivery(channel: str, exc: Exception) -> DeliveryStatus:
    message = str(exc).strip() or exc.__class__.__name__
    return DeliveryStatus(channel=channel, status="failed", detail=f"{exc.__class__.__name__}: {message}"[:500])


def telegram_blocked_by_notion(notion_status: DeliveryStatus) -> DeliveryStatus | None:
    if notion_status.status == "published":
        return None
    return DeliveryStatus(
        channel="telegram",
        status="skipped",
        detail=f"Notion status is {notion_status.status}; notification not sent.",
    )


class BriefRenderer(Protocol):
    channel: str

    def render(self, brief: IntelligenceBrief) -> str:
        ...


class BriefPublisher(Protocol):
    channel: str

    def publish(self, brief: IntelligenceBrief, rendered: str) -> DeliveryStatus:
        ...


class MarkdownBriefRenderer:
    channel = "markdown"

    def render(self, brief: IntelligenceBrief) -> str:
        brief.validate()
        lines = [
            f"# {brief.title}",
            "",
            f"- Type: {brief.brief_type}",
            f"- Domain: {brief.domain}",
            f"- Period: {brief.period_start} to {brief.period_end}",
            f"- Synthesis: {brief.synthesis_metadata.mode}/{brief.synthesis_metadata.tier}",
            "",
            "## Executive Summary",
            "",
            brief.executive_summary,
            "",
        ]
        if brief.signals:
            lines.extend(["## Top Signals", ""])
            for signal in brief.signals:
                lines.extend(
                    [
                        f"### {signal.title}",
                        "",
                        f"- Source: {signal.source_type}",
                        f"- Action: {signal.action}",
                        f"- Confidence: {signal.confidence}",
                        f"- Why now: {signal.why_now}",
                        f"- What changed: {signal.what_changed}",
                        f"- Connects to: {signal.connects_to}",
                        f"- What to do: {signal.what_to_do}",
                        "",
                        signal.rationale,
                        "",
                    ]
                )
        if brief.cross_signals:
            lines.extend(["## Cross-Signal Analysis", ""])
            for item in brief.cross_signals:
                lines.extend(
                    [
                        f"### {item.title}",
                        "",
                        f"- Subject: {item.subject}",
                        f"- Sources: {', '.join(item.sources)}",
                        f"- Confidence: {item.confidence}",
                        "",
                        item.rationale,
                        "",
                    ]
                )
        if brief.memory_links:
            lines.extend(["## Memory Links", ""])
            lines.extend(f"- {link}" for link in brief.memory_links)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


class TelegramBriefRenderer:
    channel = "telegram"

    def render(self, brief: IntelligenceBrief) -> str:
        top_lines = [f"{signal.action}: {signal.title}" for signal in brief.signals[:5]]
        body = "\n".join(f"- {line}" for line in top_lines) or "- No actionable signals."
        return f"{brief.title}\n\n{brief.executive_summary}\n\n{body}"


class MarkdownFilePublisher:
    channel = "obsidian"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def publish(self, brief: IntelligenceBrief, rendered: str) -> DeliveryStatus:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = _safe_filename(f"{brief.period_end}-{brief.brief_type}-{brief.title}.md")
        path = self.output_dir / filename
        path.write_text(rendered, encoding="utf-8")
        return DeliveryStatus(channel=self.channel, status="published", detail=str(path))


class TelegramBriefPublisher:
    channel = "telegram"

    def __init__(self, client: TelegramClient) -> None:
        self.client = client

    def publish(self, brief: IntelligenceBrief, rendered: str) -> DeliveryStatus:
        notification = TelegramNotification(
            title=brief.title,
            decisions=brief.top_actions,
            top_action=brief.signals[0].action if brief.signals else "Ignore",
            notion_url=brief.memory_links[0] if brief.memory_links else "",
            executive_summary=brief.executive_summary,
        )
        result = self.client.send_notification(notification)
        return DeliveryStatus(channel="telegram", status="sent", detail=str(result.message_id))


class TelegramNotificationPublisher:
    channel = "telegram"

    def __init__(self, client: TelegramClient, notification: TelegramNotification) -> None:
        self.client = client
        self.notification = notification

    def publish(self, brief: IntelligenceBrief, rendered: str) -> DeliveryStatus:
        result = self.client.send_notification(self.notification)
        return DeliveryStatus(channel="telegram", status="sent", detail=str(result.message_id))


class BriefDeliveryCoordinator:
    def __init__(self, renderers: dict[str, BriefRenderer], publishers: dict[str, BriefPublisher]) -> None:
        self.renderers = renderers
        self.publishers = publishers

    def deliver(self, brief: IntelligenceBrief, *, requested: tuple[str, ...] | None = None) -> tuple[DeliveryStatus, ...]:
        channels = requested or brief.delivery_hints.requested_publishers
        statuses: list[DeliveryStatus] = []
        primary_status: DeliveryStatus | None = None
        for channel in channels:
            publisher = self.publishers.get(channel)
            renderer = self.renderers.get(channel) or self.renderers.get("markdown")
            if publisher is None or renderer is None:
                status = DeliveryStatus(channel=channel, status="skipped", detail="Missing renderer or publisher.")
                statuses.append(status)
                continue
            if channel == "telegram" and brief.delivery_hints.telegram_requires_primary_success:
                if primary_status is not None and primary_status.status != "published":
                    statuses.append(
                        DeliveryStatus(
                            channel="telegram",
                            status="skipped",
                            detail=f"Primary publisher status is {primary_status.status}; notification not sent.",
                        )
                    )
                    continue
            try:
                status = publisher.publish(brief, renderer.render(brief))
            except Exception as exc:
                status = failed_delivery(channel, exc)
            statuses.append(status)
            if channel == brief.delivery_hints.primary_publisher:
                primary_status = status
        return tuple(statuses)


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:180] or "brief.md"
