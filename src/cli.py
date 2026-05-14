"""
=================================================================
  RAG Code Gen CLI — 命令行工具
  ==============================
  使用方式:
    # 爬取真实网站 → 自动入库
    python -m src.cli crawl https://www.w3schools.com/sql/ --max-pages 5

    # 用银行场景生成SQL
    python -m src.cli ask "查上月各分行可疑交易金额 TOP10" --scenario risk_monitoring

    # 用银行场景生成Python
    python -m src.cli ask "写函数计算贷款逾期率" --language python

    # 列出所有预设银行场景
    python -m src.cli scenarios

    # 查看知识库状态
    python -m src.cli status

    # 全文搜索知识库
    python -m src.cli search "GROUP BY 用法"

    # 启动服务
    python -m src.cli serve

    # 验证一段代码
    python -m src.cli validate "DROP TABLE users" --language sql
=================================================================
"""

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ 无法连接到服务器: {e}")
        print(f"   请先启动服务: python -m src.app")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ API 错误 ({e.code}): {body[:300]}")
        sys.exit(1)


def cmd_scenarios():
    """列出所有银行场景预设"""
    from src.business.banking import HSBC_DESCRIPTIONS, HSBC_SCHEMAS
    print("\n  📋 可用的银行金融场景:\n")
    for key, desc in HSBC_DESCRIPTIONS.items():
        table_count = HSBC_SCHEMAS[key].count("CREATE TABLE")
        print(f"  {key:25s}  ({table_count} tables)  {desc}")


def cmd_crawl(args):
    """爬取网站并自动入库"""
    url = args.url
    max_pages = args.max_pages
    auto_index = not getattr(args, "no_index", False)

    print(f"\n  🕷️  正在爬取: {url}")
    print(f"  📄  最大页数: {max_pages}")
    print()

    if auto_index:
        data = api("POST", "/api/v1/pipeline/crawl-and-index", {
            "url": url, "max_pages": max_pages, "crawler_type": "doc",
        })
        print(f"  ✅ 爬取 {data['crawled_count']} 篇文档")
        print(f"  📚 索引 {data['indexed_count']} 个块")
        print(f"  💾 知识库总量: {data['total_in_store']} 条")
        for src in data.get("sources", [])[:5]:
            print(f"     - {src}")
        if len(data.get("sources", [])) > 5:
            print(f"     ... 还有 {len(data['sources']) - 5} 个页面")
    else:
        data = api("POST", "/api/v1/crawl", {
            "url": url, "max_pages": max_pages, "crawler_type": "doc",
        })
        print(f"  ✅ 爬取 {data['crawled_count']} 篇文档")
        for doc in data.get("documents", [])[:5]:
            print(f"     - {doc['title'][:60]} ({len(doc['content'])} 字符)")


def cmd_search(args):
    """搜索知识库"""
    data = api("POST", "/api/v1/search", {"query": args.query, "top_k": args.top_k})
    print(f"\n  🔍 搜索: {args.query}")
    print(f"  📊 找到 {len(data['results'])} 条结果:\n")
    for i, r in enumerate(data["results"]):
        print(f"  #{i+1}  得分 {r['score']:.4f}")
        print(f"      {r['document'][:150]}...")
        print()


def cmd_ask(args):
    """用自然语言生成代码"""
    language = args.language
    scenario = args.scenario
    requirement = args.requirement

    # 加载 Schema
    table_schema = ""
    if scenario and language == "sql":
        from src.business.banking import get_schema
        table_schema = get_schema(scenario)
        if table_schema:
            print(f"\n  🏦 使用场景: {scenario}")
        else:
            print(f"\n  ⚠️  场景 '{scenario}' 不存在，使用通用模式")
            print(f"  可用场景: {', '.join(get_schema.__globals__['HSBC_SCHEMAS'].keys())}")

    print(f"  💬 需求: {requirement}")
    print(f"  🤖 正在调用 {language.upper()} 生成器...\n")

    data = api("POST", "/api/v1/pipeline/ask", {
        "requirement": requirement,
        "language": language,
        "table_schema": table_schema,
    })

    print(f"  ┌{'─'*66}┐")
    for line in data["generated_code"].split("\n")[:25]:
        print(f"  │ {line:<64} │")
    print(f"  └{'─'*66}┘")

    print(f"\n  📊 生成报告:")
    print(f"     模型:       {data['model']}")
    print(f"     耗时:       {data['generation_time_ms']:.0f}ms")
    print(f"     Token:      {data['tokens_used']}")
    print(f"     语法验证:   {'✅ 通过' if data['validation']['is_valid'] else '❌ 失败'}")
    print(f"     安全验证:   {'✅ 通过' if data['validation']['is_safe'] else '⚠️ 失败'}")
    if data['validation']['errors']:
        for e in data['validation']['errors']:
            print(f"       ⚠️  {e}")
    print(f"     沙箱执行:   {'✅ 成功' if data['sandbox_execution']['success'] else '❌ 失败'}")
    if data['sandbox_execution']['output']:
        print(f"     执行输出:   {data['sandbox_execution']['output'][:200]}")

    if data.get("retrieved_context"):
        print(f"\n  📚 检索到的相关上下文:")
        for rc in data["retrieved_context"][:2]:
            print(f"     得分 {rc['score']:.4f}: {rc['document'][:100]}...")


def cmd_validate(args):
    """验证代码"""
    data = api("POST", "/api/v1/validate", {"code": args.code, "language": args.language})
    status = "✅" if data["is_valid"] and data["is_safe"] else "❌"
    print(f"\n  {status} 验证结果:")
    print(f"     语法正确: {data['is_valid']}")
    print(f"     安全:     {data['is_safe']}")
    if data["errors"]:
        for e in data["errors"]:
            print(f"     ⚠️  {e}")


def cmd_status():
    """查看状态"""
    data = api("GET", "/api/v1/metrics")
    print(f"\n  📊 系统状态:")
    print(f"     SQL 生成次数:    {data['sql']['total_generations']}")
    print(f"     SQL 成功率:      {data['sql']['success_rate']}")
    print(f"     Python 生成次数: {data['python']['total_generations']}")
    print(f"     Python 成功率:   {data['python']['success_rate']}")
    print(f"     总 Token:        {data['total_tokens_used']}")

    from src.business.banking import HSBC_DESCRIPTIONS
    print(f"\n  🏦 可用场景: {len(HSBC_DESCRIPTIONS)} 个")
    for key, desc in HSBC_DESCRIPTIONS.items():
        print(f"     - {key}: {desc}")


def cmd_serve(args):
    """启动服务"""
    import subprocess
    print("\n  🚀 启动 RAG Code Gen 服务...")
    print(f"     地址: http://{args.host}:{args.port}")
    print(f"     文档: http://localhost:{args.port}/docs")
    print(f"     按 Ctrl+C 停止\n")
    subprocess.run([sys.executable, "-m", "src.app"])


def main():
    parser = argparse.ArgumentParser(
        prog="rag-code-gen",
        description="RAG Code Gen — 智能代码生成命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  rag-code-gen crawl https://www.w3schools.com/sql/ --max-pages 5
  rag-code-gen ask "查上月大额可疑交易TOP10" --scenario risk_monitoring
  rag-code-gen ask "写函数计算贷款逾期率" --language python
  rag-code-gen scenarios
  rag-code-gen search "JOIN 多表查询"
  rag-code-gen validate "DROP TABLE users" --language sql
  rag-code-gen status
  rag-code-gen serve
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # crawl
    p = sub.add_parser("crawl", help="爬取网站并自动索引到知识库")
    p.add_argument("url", help="要爬取的网站 URL")
    p.add_argument("--max-pages", type=int, default=10, help="最大爬取页数 (默认: 10)")
    p.add_argument("--no-index", action="store_true", dest="no_index", help="只爬取不入库")

    # ask
    p = sub.add_parser("ask", help="用自然语言生成代码 (完整管线)")
    p.add_argument("requirement", help="需求描述 (人话)")
    p.add_argument("--language", "-l", default="sql", choices=["sql", "python"], help="语言 (默认: sql)")
    p.add_argument("--scenario", "-s", default="", help="银行场景 (risk_monitoring, loan_portfolio, customer_accounts, trade_finance)")

    # search
    p = sub.add_parser("search", help="搜索知识库")
    p.add_argument("query", help="搜索关键词")
    p.add_argument("--top-k", "-k", type=int, default=5, help="返回结果数 (默认: 5)")

    # validate
    p = sub.add_parser("validate", help="验证代码安全性")
    p.add_argument("code", help="要验证的代码")
    p.add_argument("--language", "-l", default="sql", choices=["sql", "python"], help="语言")

    # scenarios
    sub.add_parser("scenarios", help="列出所有银行场景预设")

    # status
    sub.add_parser("status", help="查看系统状态")

    # serve
    p = sub.add_parser("serve", help="启动 API 服务")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "crawl":
        cmd_crawl(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "scenarios":
        cmd_scenarios()
    elif args.command == "status":
        cmd_status()
    elif args.command == "serve":
        cmd_serve(args)


if __name__ == "__main__":
    main()
