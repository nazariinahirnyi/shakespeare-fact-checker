"""Факти: речення статті -> чанк (у межах сцени абзацу). Помилки: підміна числа/імені/ролі/сцени/місця відносно чанка."""
import argparse
import difflib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

STOP = set("""a an the of to in on at by for with from and or but is are was were be been being it its this that
these those he she they we you i his her their our your him them me us as so if than then there here not no
do does did has have had says said tells asks also which who whom whose what when where while into over under""".split())
NUMS = set("""one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen
eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand first second third fourth fifth
sixth seventh eighth ninth tenth half twice thrice""".split())
ROLES = set("""father mother son daughter brother sister uncle aunt nephew niece cousin husband wife grandsire grandfather
grandmother grandson granddaughter grandchild king queen duke duchess prince princess earl lord lady knight bishop
archbishop cardinal emperor captain general servant fool ghost friend enemy murderer killer""".split())
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
MAX_ERRORS = 8


def toks(text):
    """[(token, cap)] ; cap = з великої літери і не на початку рядка/речення."""
    t = text.replace("’", "'").replace("‘", "'")
    t = re.sub(r"(?i)'s\b", "", t)
    out = []
    for line in t.splitlines():
        for i, w in enumerate(re.findall(r"[A-Za-z0-9]+", line)):
            out.append((w.lower(), i > 0 and w[0].isupper()))
    return out


def content(text):
    return [w for w, _ in toks(text) if w not in STOP]


def sentences(text):
    parts = re.split(r"(?<=[.!?])[”\"’]?\s+", " ".join(text.split()))
    return [p.strip() for p in parts if p.strip()]


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def window(raw, key, size=26):
    ws = raw.split()
    pos = 0
    for i, w in enumerate(ws):
        if key and key in " ".join(x for x, _ in toks(w)).split():
            pos = i
            break
    s = max(0, min(pos - size // 2, len(ws) - size))
    return " ".join(ws[s:s + size])


def span_candidates(S, i, typ, ct, ctset, sentset):
    """Шукає в чанку замінник для S[i] за якорями-сусідами."""
    L = R = None
    for j in range(i - 1, max(-1, i - 4), -1):
        if S[j][0] not in STOP and S[j][0] in ctset:
            L = S[j][0]; break
    for j in range(i + 1, min(len(S), i + 4)):
        if S[j][0] not in STOP and S[j][0] in ctset:
            R = S[j][0]; break
    pl = [k for k, (c, _) in enumerate(ct) if c == L] if L else []
    pr = [k for k, (c, _) in enumerate(ct) if c == R] if R else []
    idx, anchors = set(), 0
    for a in pl:
        for b in pr:
            if 0 < b - a <= 9:
                idx.update(range(a + 1, b)); anchors = 2
    if not idx:
        for a in pl:
            idx.update(range(a + 1, a + 6)); anchors = max(anchors, 1)
        for b in pr:
            idx.update(range(max(0, b - 5), b)); anchors = max(anchors, 1)
    res = []
    for k in idx:
        if k >= len(ct):
            continue
        c, cap = ct[k]
        if c in STOP or c in sentset:
            continue
        ok = (typ == "num" and (c in NUMS or c.isdigit())) or (typ == "role" and c in ROLES) or (typ == "prop" and cap)
        if ok:
            res.append((c, anchors))
    return res


def token_errors(sent, S, ct, ctset, raw):
    sentset = {w for w, _ in S}
    best = None
    for i, (t, cap) in enumerate(S):
        if t in STOP or t in ctset:
            continue
        typ = "num" if (t in NUMS or t.isdigit()) else "role" if t in ROLES else "prop" if cap else None
        if not typ:
            continue
        if typ == "prop" and any(sim(t, c) >= 0.85 for c in ctset):
            continue  # орфографічний варіант імені
        cands = span_candidates(S, i, typ, ct, ctset, sentset)
        if not cands:
            continue
        c, anc = max(cands, key=lambda x: (x[1], sim(t, x[0])))
        conf = (0.9 if anc == 2 else 0.65) + (0.05 if typ == "num" else 0)
        if best is None or conf > best[0]:
            best = (conf, t, c, window(raw, c))
    return best


def roman_or_int(s):
    s = s.lower()
    return int(s) if s.isdigit() else ROMAN.get(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()

    chunks, df = {}, Counter()
    groups = defaultdict(list)
    for line in Path(a.input, "corpus.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ct = toks(r["text"])
        cs = {w for w, _ in ct if w not in STOP}
        chunks[r["id"]] = {"raw": r["text"], "ct": ct, "set": cs, "meta": r}
        groups[r["id"].split("#")[0]].append(r["id"])
        df.update(cs)
    N = len(chunks)
    idf = {w: math.log((N + 1) / (c + 1)) + 1 for w, c in df.items()}

    def score(qs, cid):
        den = sum(idf.get(w, 1) for w in qs) or 1
        return sum(idf.get(w, 1) for w in qs & chunks[cid]["set"]) / den

    Path(a.output).mkdir(parents=True, exist_ok=True)
    for p in sorted(Path(a.input, "articles").glob("article_*.json")):
        art = json.loads(p.read_text(encoding="utf-8-sig"))
        facts, errs, seen = [], [], set()
        for para in re.split(r"\n\s*\n", art["text"]):
            sents = [s for s in sentences(para) if s not in seen]
            qsets = [set(content(s)) for s in sents]
            # сцена абзацу = група чанків із найбільшою сумою найкращих збігів
            gscore = {}
            for g, ids in groups.items():
                gscore[g] = sum(max(score(q, c) for c in ids) for q in qsets if q)
            gbest = max(gscore, key=gscore.get) if gscore else None
            for sent, qs in zip(sents, qsets):
                seen.add(sent)
                if not qs:
                    continue
                allids = list(chunks)
                gids = groups[gbest] if gbest else allids
                cid = max(gids, key=lambda c: score(qs, c))
                gid = max(allids, key=lambda c: score(qs, c))
                if score(qs, gid) - score(qs, cid) > 0.25:
                    cid = gid
                if len(sent.split()) <= 40:
                    facts.append({"text": sent, "source_chunk": cid})
                if len(sent.split()) > 60:
                    continue
                ch = chunks[cid]
                S = toks(sent)
                cand = None
                g = groups[cid.split("#")[0]]
                # 1) номер сцени/акту за метаданими
                m = re.search(r"(?i)\bscene\s+([ivx]+|\d+)\b", sent)
                meta = ch["meta"]
                if m and meta.get("scene") is not None:
                    n = roman_or_int(m.group(1))
                    lo, hi = meta["scene"], meta.get("scene_to") or meta["scene"]
                    if n is not None and not (lo <= n <= hi):
                        true_roman = {v: k.upper() for k, v in ROMAN.items()}.get(lo, str(lo))
                        cand = (0.95, f"Scene {m.group(1)}", f"Scene {true_roman}", window(ch["raw"], "scene"))
                # 2) місце дії: 'set in X' проти заголовка 'SCENE I. Place.'
                if not cand:
                    pm = re.search(r"\bset in ([A-Z][A-Za-z]+)", sent)
                    if pm:
                        for gid_ in g:
                            hm = re.search(r"SCENE\s+[IVXLC\d]+\s*[.:,]?\s*([A-Z][A-Za-z]+)", chunks[gid_]["raw"])
                            if hm and sim(pm.group(1).lower(), hm.group(1).lower()) < 0.85:
                                cand = (0.9, pm.group(1), hm.group(1), window(chunks[gid_]["raw"], hm.group(1).lower()))
                                cid = gid_
                                break
                # 3) підміна числа / імені / ролі
                if not cand and score(qs, cid) >= 0.5:
                    te = token_errors(sent, S, ch["ct"], ch["set"], ch["raw"])
                    if te:
                        cand = te
                if cand:
                    errs.append((cand[0], {"sentence": sent, "wrong": cand[1], "correct": cand[2],
                                           "source_chunk": cid, "source_quote": cand[3]}))
        errs.sort(key=lambda x: -x[0])
        out = {"article": art["article"], "facts": facts[:200], "errors": [e for _, e in errs[:MAX_ERRORS]]}
        Path(a.output, p.name).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("готово")


if __name__ == "__main__":
    main()