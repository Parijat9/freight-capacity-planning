"""Read-only Zoho CRM V8 extraction. Import only approved, de-identified exports."""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch_deals(token, domain="https://www.zohoapis.com", opener=urlopen):
    allowed = {
        "https://www.zohoapis.com",
        "https://www.zohoapis.eu",
        "https://www.zohoapis.in",
        "https://www.zohoapis.com.au",
    }
    if domain not in allowed:
        raise ValueError("Unsupported Zoho data center")
    page = 1
    next_token = None
    seen = set()
    records = []
    while True:
        params = {
            "fields": "id,Stage,Amount,Closing_Date,Modified_Time",
            "per_page": 200,
        }
        params.update({"page_token": next_token} if next_token else {"page": page})
        request = Request(
            domain + "/crm/v8/Deals?" + urlencode(params),
            headers={"Authorization": "Zoho-oauthtoken " + token},
            method="GET",
        )
        with opener(request, timeout=30) as response:
            if response.status == 204:
                break
            payload = json.load(response)
        for row in payload.get("data", []):
            if row["id"] in seen:
                raise ValueError(
                    "Duplicate deal across pages; use a stable extraction snapshot"
                )
            seen.add(row["id"])
            records.append(row)
        info = payload.get("info", {})
        if not info.get("more_records"):
            break
        if page < 10 and next_token is None:
            page += 1
        else:
            token_next = info.get("next_page_token")
            if not token_next or token_next == next_token:
                raise ValueError("Missing or repeated page token")
            next_token = token_next
        if len(records) >= 100000:
            raise ValueError("Partition extraction above API paging limit")
    return records
