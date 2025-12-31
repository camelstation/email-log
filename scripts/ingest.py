import base64
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple, List

import cloudinary
import cloudinary.uploader
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

ALLOWED_FROM = "campbell.watson@gmail.com"

# Optional: only process messages that have this label.
# If you leave it None, we process unread INBOX messages (still safe due to ALLOWED_FROM enforcement).
INBOX_LABEL_QUERY = None  # e.g. "label:log"
PROCESSED_LABEL_NAME = "processed-email-log"


URL_RE = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)


def normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def load_entries(path: str) -> dict:
    if not os.path.exists(path):
        return {"entries": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def get_header(headers: List[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def extract_text_from_payload(payload: dict) -> str:
    # Prefer text/plain, fallback to html stripped
    def decode_body(data: str) -> str:
        raw = base64.urlsafe_b64decode(data.encode("utf-8"))
        return raw.decode("utf-8", errors="replace")

    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {}) or {}
    data = body.get("data")

    if mime_type == "text/plain" and data:
        return decode_body(data)

    if mime_type == "text/html" and data:
        html = decode_body(data)
        return BeautifulSoup(html, "html.parser").get_text("\n")

    parts = payload.get("parts", []) or []
    # Look for text/plain in parts
    for p in parts:
        if p.get("mimeType") == "text/plain" and (p.get("body", {}) or {}).get("data"):
            return decode_body(p["body"]["data"])

    # Fallback to html part
    for p in parts:
        if p.get("mimeType") == "text/html" and (p.get("body", {}) or {}).get("data"):
            html = decode_body(p["body"]["data"])
            return BeautifulSoup(html, "html.parser").get_text("\n")

    # As a last resort, recursively search nested multiparts
    for p in parts:
        if p.get("parts"):
            t = extract_text_from_payload(p)
            if t.strip():
                return t

    return ""


def extract_first_url_and_remove(text: str) -> Tuple[str, Optional[str]]:
    m = URL_RE.search(text)
    if not m:
        return text.strip(), None
    url = m.group(1).strip()
    # remove the raw URL from the body
    new_text = (text[:m.start()] + text[m.end():]).strip()
    # If URL was on its own line, this also collapses cleanly
    new_text = re.sub(r"\n{3,}", "\n\n", new_text).strip()
    return new_text, url


def find_attachments(payload: dict) -> List[dict]:
    out = []

    def walk(part: dict):
        filename = part.get("filename") or ""
        body = part.get("body", {}) or {}
        attachment_id = body.get("attachmentId")
        mime_type = part.get("mimeType") or ""
        if filename and attachment_id:
            out.append({"filename": filename, "attachmentId": attachment_id, "mimeType": mime_type})
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return out


def ensure_label(service, user_id: str, label_name: str) -> str:
    labels = service.users().labels().list(userId=user_id).execute().get("labels", [])
    for lab in labels:
        if lab.get("name") == label_name:
            return lab["id"]
    created = service.users().labels().create(
        userId=user_id,
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    return created["id"]


def upload_first_photo_to_cloudinary(message_id: str, filename: str, data_bytes: bytes) -> Tuple[str, str]:
    # Configure Cloudinary from env
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )

    # Put everything under a folder so it’s easy to manage
    public_id = f"email-log/{message_id}-{uuid.uuid4().hex}"
    res = cloudinary.uploader.upload(
        data_bytes,
        public_id=public_id,
        resource_type="image",
        overwrite=False,
    )
    return res["secure_url"], res["public_id"]


def destroy_cloudinary_asset(public_id: str) -> None:
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    # destroy is part of Upload API capabilities (SDK wraps it)
    cloudinary.uploader.destroy(public_id, invalidate=True)


def main():
    # Auth
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("gmail", "v1", credentials=creds)

    user_id = "me"
    processed_label_id = ensure_label(service, user_id, PROCESSED_LABEL_NAME)

    entries_path = os.path.join("data", "entries.json")
    state = load_entries(entries_path)
    entries = state.get("entries", [])

    # Query unread messages
    q_parts = ["is:unread", "in:inbox"]
    if INBOX_LABEL_QUERY:
        q_parts.append(INBOX_LABEL_QUERY)
    q = " ".join(q_parts)

    resp = service.users().messages().list(userId=user_id, q=q, maxResults=25).execute()
    msgs = resp.get("messages", []) or []
    if not msgs:
        print("No unread messages to process.")
        return

    changed = False

    # Sort oldest-first so processing is stable
    for m in reversed(msgs):
        msg_id = m["id"]
        full = service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()

        payload = full.get("payload", {}) or {}
        headers = payload.get("headers", []) or []
        from_header = get_header(headers, "From")
        subject = get_header(headers, "Subject").strip()
        internal_ms = int(full.get("internalDate", "0"))
        created_ts = int(internal_ms // 1000)

        if ALLOWED_FROM not in from_header:
            print(f"Skipping message {msg_id}: from={from_header}")
            # mark as read + processed label so it doesn't re-run forever
            service.users().messages().modify(
                userId=user_id,
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"], "addLabelIds": [processed_label_id]},
            ).execute()
            continue

        body_text = extract_text_from_payload(payload)
        body_lower = body_text.lower()

        has_add = "[add]" in body_lower
        has_delete = "[delete]" in body_lower

        if not (has_add or has_delete):
            print(f"Ignoring message {msg_id}: no [add]/[delete]")
            service.users().messages().modify(
                userId=user_id,
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"], "addLabelIds": [processed_label_id]},
            ).execute()
            continue

        # If both appear, treat as ignore (safer)
        if has_add and has_delete:
            print(f"Ignoring message {msg_id}: contains both [add] and [delete]")
            service.users().messages().modify(
                userId=user_id,
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"], "addLabelIds": [processed_label_id]},
            ).execute()
            continue

        if has_add:
            cleaned = re.sub(r"\[add\]", "", body_text, flags=re.IGNORECASE).strip()
            cleaned, link_url = extract_first_url_and_remove(cleaned)

            # Attachment handling: upload first image attachment only (easy to extend)
            photo_url = None
            photo_public_id = None
            atts = find_attachments(payload)

            if atts:
                # take first attachment that looks like an image
                img = None
                for a in atts:
                    mt = (a.get("mimeType") or "").lower()
                    fn = (a.get("filename") or "").lower()
                    if mt.startswith("image/") or fn.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic")):
                        img = a
                        break

                if img:
                    att = service.users().messages().attachments().get(
                        userId=user_id, messageId=msg_id, id=img["attachmentId"]
                    ).execute()
                    data_b64 = att.get("data", "")
                    data_bytes = base64.urlsafe_b64decode(data_b64.encode("utf-8"))
                    photo_url, photo_public_id = upload_first_photo_to_cloudinary(msg_id, img["filename"], data_bytes)

            dt = datetime.fromtimestamp(created_ts, tz=timezone.utc).date().isoformat()

            entry = {
                "id": str(uuid.uuid4()),
                "created_ts": created_ts,
                "date": dt,
                "category": subject.lower() if subject else "",
                "text": cleaned,
                "normalized_text": normalize_text(cleaned),
                "link_url": link_url or "",
                "photo_url": photo_url or "",
                "photo_public_id": photo_public_id or "",
            }
            entries.append(entry)
            changed = True
            print(f"Added entry from {msg_id}")

        if has_delete:
            needle = re.sub(r"\[delete\]", "", body_text, flags=re.IGNORECASE).strip()
            needle_norm = normalize_text(needle)

            # newest-first search
            entries_sorted = sorted(entries, key=lambda e: e.get("created_ts", 0), reverse=True)
            target = None
            for e in entries_sorted:
                if e.get("normalized_text", "") == needle_norm:
                    target = e
                    break

            if target:
                if target.get("photo_public_id"):
                    try:
                        destroy_cloudinary_asset(target["photo_public_id"])
                    except Exception as ex:
                        # deletion is optional; don't block log updates
                        print(f"Cloudinary delete failed for {target['photo_public_id']}: {ex}")

                entries = [e for e in entries if e.get("id") != target.get("id")]
                changed = True
                print(f"Deleted entry matching: {needle_norm}")
            else:
                print(f"No match for delete: {needle_norm}")

        # mark processed
        service.users().messages().modify(
            userId=user_id,
            id=msg_id,
            body={"removeLabelIds": ["UNREAD"], "addLabelIds": [processed_label_id]},
        ).execute()

    if changed:
        # newest-first order
        entries = sorted(entries, key=lambda e: e.get("created_ts", 0), reverse=True)

        # strip normalized_text from the public JSON if you want; keeping it is fine too
        state["entries"] = entries
        atomic_write_json(entries_path, state)
        print(f"Wrote {entries_path} with {len(entries)} entries.")
    else:
        print("No changes to entries.json")


if __name__ == "__main__":
    main()

