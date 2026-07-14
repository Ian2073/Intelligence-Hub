from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from core.memory import MemoryStore
from core.proposal_service import ProposalTrustService
from core.proposal_store import SQLiteProposalStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect and review Intelligence Hub proposals.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List proposals.")
    list_parser.add_argument("--status", choices=("pending", "accepted", "rejected", "needs_review"))

    revalidate_parser = subparsers.add_parser("revalidate", help="Re-run Proposal Gate for a proposal.")
    revalidate_parser.add_argument("proposal_id")

    accept_parser = subparsers.add_parser("accept", help="Accept a needs-review proposal after required validation.")
    accept_parser.add_argument("proposal_id")

    reject_parser = subparsers.add_parser("reject", help="Reject a proposal with an audit reason.")
    reject_parser.add_argument("proposal_id")
    reject_parser.add_argument("--reason", required=True)

    args = parser.parse_args(argv)
    settings = load_settings(PROJECT_ROOT)
    store = MemoryStore(settings.memory_db)
    try:
        proposals = SQLiteProposalStore.from_memory_store(store)
        service = ProposalTrustService(store=store, proposals=proposals)
        if args.command == "list":
            for proposal in proposals.list(status=args.status):
                reasons = "; ".join(proposal.rejection_reasons)
                print(
                    f"{proposal.id}\t{proposal.validation_status}\t{proposal.proposal_type}\t"
                    f"proposed_by={proposal.proposed_by}\treasons={reasons}"
                )
            return 0
        if args.command == "revalidate":
            result = service.submit(proposals.get(args.proposal_id))
            print(
                f"{result.proposal.id}\t{result.proposal.validation_status}\t"
                f"canonical={result.proposal.accepted_canonical_id}\t"
                f"reasons={'; '.join(result.proposal.rejection_reasons)}"
            )
            return 0
        if args.command == "accept":
            result = service.accept_needs_review(args.proposal_id)
            print(f"{result.proposal.id}\t{result.proposal.validation_status}\tcanonical={result.canonical_id}")
            return 0
        if args.command == "reject":
            proposal = service.reject(args.proposal_id, reason=args.reason)
            print(f"{proposal.id}\t{proposal.validation_status}\treasons={'; '.join(proposal.rejection_reasons)}")
            return 0
    finally:
        store.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
