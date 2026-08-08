from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.fxbaogao_report_runner import (
    collect_fxbaogao_report_search,
    fetch_fxbaogao_paragraphs,
    filter_fxbaogao_report_candidates,
    load_fxbaogao_api_key,
)


class FxbaogaoReportRunnerTests(unittest.TestCase):
    def test_loads_api_key_from_fxbaogao_section_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault.txt"
            vault.write_text("[other]\napi_key = wrong\n\n[fxbaogao]\napi_key = expected\n", encoding="utf-8")
            self.assertEqual(load_fxbaogao_api_key(vault), "expected")

    def test_search_writes_manifest_and_candidates_without_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault.txt"
            vault.write_text("[fxbaogao]\napi_key = test-secret\n", encoding="utf-8")

            def fake_post(path: str, payload: dict, api_key: str) -> dict:
                self.assertEqual(path, "/mofoun/agent/search")
                self.assertEqual(api_key, "test-secret")
                self.assertEqual(payload["keywords"], "保险 内含价值")
                return {
                    "code": 0,
                    "msg": "ok",
                    "data": [
                        {
                            "reportId": 123,
                            "title": "<em>保险</em>行业报告",
                            "orgName": "测试证券",
                            "industryName": "非银金融",
                            "pageNum": 20,
                            "pubTime": 1700000000,
                            "pubTimeStr": "2024/01/01",
                            "paragraphs": [{"content": "hit"}],
                        }
                    ],
                }

            manifest_path = collect_fxbaogao_report_search("保险 内含价值", root / "out", vault_path=vault, http_post=fake_post)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            self.assertEqual(manifest["report_count"], 1)
            self.assertNotIn("test-secret", manifest_path.read_text(encoding="utf-8-sig"))
            with (root / "out" / "report_candidates.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["report_id"], "123")
            self.assertEqual(rows[0]["title"], "保险行业报告")
            self.assertEqual(rows[0]["view_url"], "https://www.fxbaogao.com/view?id=123")

    def test_paragraph_fetch_writes_report_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault.txt"
            vault.write_text("[fxbaogao]\napi_key = test-secret\n", encoding="utf-8")

            def fake_post(path: str, payload: dict, api_key: str) -> dict:
                self.assertEqual(path, "/mofoun/agent/paragraph")
                self.assertEqual(payload["reportId"], 123)
                return {
                    "code": 0,
                    "msg": "ok",
                    "data": {
                        "title": "保险报告",
                        "summary": "摘要",
                        "paragraphs": [{"pageNum": 5, "content": "内含价值段落"}],
                    },
                }

            csv_path = fetch_fxbaogao_paragraphs(123, "内含价值", root / "out", vault_path=vault, http_post=fake_post)
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["content"], "内含价值段落")
            self.assertEqual(rows[0]["view_url"], "https://www.fxbaogao.com/view?id=123")

    def test_filter_candidates_excludes_noisy_titles_and_ranks_relevant_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "report_candidates.csv"
            with candidates.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "report_id",
                        "title",
                        "org_name",
                        "industry_name",
                        "page_num",
                        "pub_time",
                        "pub_time_str",
                        "view_url",
                        "paragraph_hit_count",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "report_id": "1",
                        "title": "红利低波策略专题：回撤控制与风险预算",
                        "org_name": "测试证券",
                        "industry_name": "金融工程",
                        "page_num": "30",
                        "pub_time": "1",
                        "pub_time_str": "2026/01/01",
                        "view_url": "https://www.fxbaogao.com/view?id=1",
                        "paragraph_hit_count": "2",
                    }
                )
                writer.writerow(
                    {
                        "report_id": "2",
                        "title": "红利低波周报：市场跟踪",
                        "org_name": "测试证券",
                        "industry_name": "策略",
                        "page_num": "8",
                        "pub_time": "2",
                        "pub_time_str": "2026/01/02",
                        "view_url": "https://www.fxbaogao.com/view?id=2",
                        "paragraph_hit_count": "1",
                    }
                )

            manifest = filter_fxbaogao_report_candidates(
                [candidates],
                root / "filtered",
                include_all=["红利低波"],
                include_any=["回撤", "风险预算"],
            )
            with manifest.open(encoding="utf-8-sig") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["accepted_count"], 1)
            with (root / "filtered" / "filtered_report_candidates.csv").open(
                encoding="utf-8-sig", newline=""
            ) as handle:
                accepted = list(csv.DictReader(handle))
            self.assertEqual(accepted[0]["report_id"], "1")
            with (root / "filtered" / "rejected_report_candidates.csv").open(
                encoding="utf-8-sig", newline=""
            ) as handle:
                rejected = list(csv.DictReader(handle))
            self.assertEqual(rejected[0]["report_id"], "2")
            self.assertIn("title_excluded", rejected[0]["rejection_reason"])


if __name__ == "__main__":
    unittest.main()
