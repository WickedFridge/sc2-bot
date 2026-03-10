from enum import Enum


class SwapState(str, Enum):
    """
    Lifecycle of an addon swap between a donor and a recipient building.
    Two possible initiation paths depending on which building finishes first:

    Path A — donor (addon) ready first:
      PENDING → DONOR_LIFTING → RECIPIENT_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE

    Path B — recipient ready first:
      PENDING → RECIPIENT_LIFTING_FIRST → DONOR_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE

    Detach-only path (AddonDetachSwap):
      PENDING → DONOR_LIFTING → DONOR_LANDING → DONE
    """

    PENDING = "PENDING"
    DONOR_LIFTING = "DONOR_LIFTING"
    RECIPIENT_LIFTING_FIRST = "RECIPIENT_LIFTING_FIRST"
    RECIPIENT_LIFTING = "RECIPIENT_LIFTING"
    RECIPIENT_LANDING = "RECIPIENT_LANDING"
    DONOR_LANDING = "DONOR_LANDING"
    DONE = "DONE"
    ABORTED = "ABORTED"