import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:4173"


def get(path: str):
    with urllib.request.urlopen(BASE + path) as r:
        return r.status, r.read()


def main() -> None:
    st, body = get("/")
    print("home", st, len(body), b"root" in body)
    st, _ = get("/privacy")
    print("privacy", st)
    st, pdf = get("/prices/optovyy-prays.pdf")
    print("pdf", st, len(pdf), pdf[:5])
    st, robots = get("/robots.txt")
    print("robots", st, robots[:40])
    # first product image from json
    products = json.loads(open("data/products.json", encoding="utf-8").read())
    img = next(p["images"][0] for p in products if p["images"])
    st, blob = get(img)
    print("image", img, st, len(blob), blob[:3])
    req = urllib.request.Request(
        BASE + "/api/wholesale-lead",
        data=json.dumps({"name": "Тест", "contact": "+7999", "consent": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        print("lead", r.status, r.read().decode("utf-8"))
    req2 = urllib.request.Request(
        BASE + "/api/wholesale-lead",
        data=json.dumps({"name": "Тест", "contact": "+7999", "consent": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req2)
    except urllib.error.HTTPError as e:
        print("lead no consent", e.code, e.read().decode("utf-8"))


if __name__ == "__main__":
    main()
