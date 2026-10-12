"""Local, opt-in matchmaking drafts. No Discord messages are sent here."""
import copy
import uuid
from datetime import datetime, timedelta, timezone
from community import CommunityError, parse_time, utcnow

def validate_listing(game, mode, rank, slots, starts_at, now=None):
    now = now or utcnow()
    values = []
    for name, value, maximum in (("Spiel", game, 60), ("Modus", mode, 60), ("Rang", rank, 60)):
        if not isinstance(value, str) or len(value.strip()) > maximum or (name != "Rang" and not value.strip()):
            raise CommunityError(name + " ungültig (maximal 60 Zeichen).")
        values.append(value.strip())
    if type(slots) is not int or not 1 <= slots <= 20:
        raise CommunityError("Gesuchte Plätze müssen zwischen 1 und 20 liegen.")
    start = parse_time(starts_at)
    if not now <= start <= now + timedelta(days=30):
        raise CommunityError("Startzeit muss innerhalb der nächsten 30 Tage liegen.")
    return dict(game=values[0], mode=values[1], rank=values[2], slots=slots, starts_at=start.isoformat())

def _find(store, guild, listing_id):
    row = next((x for x in store.guild(guild).setdefault("matchmaking", []) if x["id"] == listing_id), None)
    if row is None:
        raise CommunityError("Mitspielersuche nicht gefunden.")
    return row

def _change(store, guild, operation):
    before = copy.deepcopy(store.data)
    try:
        result = operation()
        store.save()
        return copy.deepcopy(result)
    except Exception:
        store.data = before
        raise

def create_listing(store, guild, owner_id, game, mode, rank, slots, starts_at, now=None):
    if not isinstance(owner_id, str) or not owner_id.isdecimal() or not 1 <= len(owner_id) <= 20:
        raise CommunityError("Gültige Discord-Mitglieds-ID erforderlich.")
    fields = validate_listing(game, mode, rank, slots, starts_at, now)
    def operation():
        rows = store.guild(guild).setdefault("matchmaking", [])
        if sum(r["owner_id"] == owner_id and r["status"] == "open" for r in rows) >= 3:
            raise CommunityError("Maximal drei offene Gesuche pro Mitglied.")
        row = dict(id=uuid.uuid4().hex, owner_id=owner_id, members=[], status="open", created_at=utcnow().isoformat(), **fields)
        rows.append(row)
        return row
    return _change(store, guild, operation)

def join_listing(store, guild, listing_id, member_id, now=None):
    if not isinstance(member_id, str) or not member_id.isdecimal() or not 1 <= len(member_id) <= 20:
        raise CommunityError("Gültige Discord-Mitglieds-ID erforderlich.")
    def operation():
        row = _find(store, guild, listing_id)
        if row["status"] != "open" or parse_time(row["starts_at"]) < (now or utcnow()):
            raise CommunityError("Dieses Gesuch ist nicht mehr offen.")
        if member_id == row["owner_id"] or member_id in row["members"]:
            raise CommunityError("Mitglied ist bereits in der Gruppe.")
        if len(row["members"]) >= row["slots"]:
            raise CommunityError("Die Gruppe ist bereits voll.")
        row["members"].append(member_id)
        if len(row["members"]) == row["slots"]:
            row["status"] = "full"
        return row
    return _change(store, guild, operation)

def leave_listing(store, guild, listing_id, member_id):
    def operation():
        row = _find(store, guild, listing_id)
        if member_id not in row["members"]:
            raise CommunityError("Mitglied ist nicht in dieser Gruppe.")
        row["members"].remove(member_id)
        if row["status"] == "full":
            row["status"] = "open"
        return row
    return _change(store, guild, operation)

def close_listing(store, guild, listing_id, owner_id):
    def operation():
        row = _find(store, guild, listing_id)
        if row["owner_id"] != owner_id:
            raise CommunityError("Nur die erstellende Person darf das Gesuch schließen.")
        row["status"] = "closed"
        return row
    return _change(store, guild, operation)

def active_listings(store, guild, now=None):
    now = now or utcnow()
    return [copy.deepcopy(r) for r in store.guild(guild).setdefault("matchmaking", [])
            if r["status"] in ("open", "full") and parse_time(r["starts_at"]) >= now]
