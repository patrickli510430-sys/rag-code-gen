import urllib.request, json

URL = "http://localhost:8000/api/v1"
OK = 0
FAIL = 0

def test(name, path, body=None, timeout=120):
    global OK, FAIL
    try:
        url = URL + path
        d = json.dumps(body).encode() if body else None
        r = urllib.request.Request(url, data=d, method="POST" if body else "GET")
        r.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(r, timeout=timeout)
        data = json.loads(resp.read().decode())
        OK += 1
        return True, data
    except Exception as e:
        FAIL += 1
        return False, str(e)[:150]


# get DDL
ddl = json.loads(urllib.request.urlopen(URL + "/scenarios/risk_monitoring").read())["ddl"]

tests = [
    ("01-health", "/../health"),
    ("02-dashboard-status", "/dashboard/status"),
    ("03-scenarios-list", "/scenarios"),
    ("04-scenario-detail", "/scenarios/risk_monitoring"),
    ("05-metrics", "/metrics"),
    ("06-index", "/documents/index", {"documents": [{"content": "反洗钱管理办法规定金融机构应建立客户身份识别制度与可疑交易报告制度。", "url": "test/v2/001"}]}),
    ("07-search", "/search", {"query": "反洗钱", "top_k": 2}),
    ("08-qa", "/documents/qa", {"question": "反洗钱制度要求是什么？"}),
    ("09-review", "/documents/review", {"title": "客户身份识别报告", "content": "本行已完成客户身份识别。可疑交易已上报。"}),
    ("10-classify", "/documents/classify", {"title": "反洗钱管理办法", "content": "金融机构应当建立客户身份识别制度。对个人客户单笔现金交易超过20万元应报告。"}),
    ("11-sql-gen", "/sql/generate", {"requirement": "统计每种alert_type的数量", "table_schema": ddl, "use_rag": False}),
    ("12-py-gen", "/python/generate", {"requirement": "计算两个日期之间工作日天数", "use_rag": False}),
    ("13-validate-ok", "/validate", {"code": "SELECT alert_type,COUNT(*) FROM suspicious_transactions GROUP BY alert_type;", "language": "sql"}),
    ("14-validate-danger", "/validate", {"code": "DROP TABLE users;", "language": "sql"}),
    ("15-validate-broken", "/validate", {"code": "SELECT a\n) SELECT b;", "language": "sql"}),
    ("16-execute", "/execute", {"code": "SELECT alert_type FROM suspicious_transactions LIMIT 1;", "language": "sql", "table_schema": ddl}),
    ("17-pipeline", "/pipeline/ask", {"requirement": "统计各风险等级数量", "language": "sql", "table_schema": ddl}),
]

for t in tests:
    name = t[0]
    path = t[1]
    body = t[2] if len(t) > 2 else None
    ok, data = test(name, path, body)
    mark = "[OK]" if ok else "[FAIL]"
    detail = ""
    if ok and isinstance(data, dict):
        if "is_valid" in data:
            detail = " valid={} safe={}".format(data.get("is_valid"), data.get("is_safe"))
        elif "success" in data:
            detail = " success={}".format(data.get("success"))
        elif "sql" in data:
            detail = " sql_len={}".format(len(data.get("sql", "")))
        elif "classification" in data:
            c = data.get("classification", {})
            detail = " type={} risk={}".format(c.get("doc_type", "?"), c.get("risk_level", "?"))
        elif "answer" in data:
            detail = " answer_len={}".format(len(data.get("answer", "")))
        elif "results" in data:
            detail = " results={}".format(len(data.get("results", [])))
        elif "indexed_count" in data:
            detail = " indexed={} total={}".format(data.get("indexed_count"), data.get("total_in_store"))
    print("{} {}{}".format(mark, name, detail))
    if not ok:
        print("      {}".format(data[:150]))

print("\nPASS={} FAIL={}".format(OK, FAIL))
