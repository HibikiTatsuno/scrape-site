#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import argparse
import os
from typing import Dict, Any, Optional
import urllib3

from crawl4ai import CrawlerHub
from crawl4ai.extractors import HTMLExtractor

# SSLの警告を無効化
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_sokudan_with_crawl4ai(url: str) -> Dict[str, Any]:
    """
    Crawl4AIを使ってSOKUDANの案件ページから情報を抽出してJSONに整形する
    
    Args:
        url: スクレイピングするURL
        
    Returns:
        Dict: 抽出したデータを含む辞書
    """
    # Crawl4AIのクローラーを初期化
    crawler = CrawlerHub()
    
    # SSLの検証を無効化
    crawler.config.requests_verify = False
    
    # HTMLエクストラクタを設定
    extractor = HTMLExtractor()
    
    # スクレイピングするデータのスキーマを定義
    schema = {
        "job_title": {
            "selector": "h1", 
            "extract": "text"
        },
        "job_types": {
            "selector": ".single-job__attributes a", 
            "extract": "text", 
            "multiple": True
        },
        "required_hours": {
            "selector": ".single-job__info-item:contains('稼働時間') .single-job__info-item-value", 
            "extract": "text"
        },
        "salary": {
            "selector": ".single-job__info-item:contains('報酬') .single-job__info-item-value", 
            "extract": "text"
        },
        "area": {
            "selector": ".single-job__info-item:contains('エリア') .single-job__info-item-value", 
            "extract": "text"
        },
        "required_skills": {
            "selector": ".single-job__skills a", 
            "extract": "text", 
            "multiple": True
        },
        "job_details": {
            "selector": ".single-job__body", 
            "extract": "text"
        }
    }
    
    try:
        # URLにアクセスしてデータを抽出
        extracted_data = crawler.extract(url, extractor, schema=schema)
        
        # 抽出したデータを整形
        job_data = {
            "title": extracted_data.get("job_title", ""),
            "job_type": extracted_data.get("job_types", []),
            "required_hours": extracted_data.get("required_hours", ""),
            "salary": extracted_data.get("salary", ""),
            "area": extracted_data.get("area", ""),
            "required_skills": extracted_data.get("required_skills", []),
            "details": extracted_data.get("job_details", ""),
            "url": url,
            "conditions": {}
        }
        
        # 条件を抽出
        details = job_data["details"]
        conditions = {}
        
        if "【必須条件】" in details:
            required_start = details.find("【必須条件】")
            required_end = details.find("【", required_start + 1) if details.find("【", required_start + 1) > 0 else len(details)
            conditions["required"] = details[required_start:required_end].strip()
        
        if "【歓迎条件】" in details:
            preferred_start = details.find("【歓迎条件】")
            preferred_end = details.find("【", preferred_start + 1) if details.find("【", preferred_start + 1) > 0 else len(details)
            conditions["preferred"] = details[preferred_start:preferred_end].strip()
            
        if "【想定報酬】" in details:
            salary_start = details.find("【想定報酬】")
            salary_end = details.find("【", salary_start + 1) if details.find("【", salary_start + 1) > 0 else len(details)
            conditions["expected_salary"] = details[salary_start:salary_end].strip()
        
        if "【勤務条件】" in details:
            work_cond_start = details.find("【勤務条件】")
            work_cond_end = details.find("【", work_cond_start + 1) if details.find("【", work_cond_start + 1) > 0 else len(details)
            conditions["work_conditions"] = details[work_cond_start:work_cond_end].strip()
        
        job_data["conditions"] = conditions
        
        return job_data
        
    except Exception as e:
        print(f"エラー: Crawl4AIでのスクレイピング中に問題が発生しました: {e}")
        return {}

def scrape_generic_with_crawl4ai(url: str) -> Dict[str, Any]:
    """
    Crawl4AIを使って一般的なWebサイトから情報を抽出する
    
    Args:
        url: スクレイピングするURL
        
    Returns:
        Dict: 抽出したデータを含む辞書
    """
    # Crawl4AIのクローラーを初期化
    crawler = CrawlerHub()
    
    # SSLの検証を無効化
    crawler.config.requests_verify = False
    
    # HTMLエクストラクタを設定
    extractor = HTMLExtractor()
    
    # スクレイピングするデータのスキーマを定義
    schema = {
        "title": {
            "selector": "title", 
            "extract": "text"
        },
        "meta_description": {
            "selector": "meta[name='description']", 
            "extract": "content"
        },
        "h1_headings": {
            "selector": "h1", 
            "extract": "text", 
            "multiple": True
        },
        "h2_headings": {
            "selector": "h2", 
            "extract": "text", 
            "multiple": True
        },
        "h3_headings": {
            "selector": "h3", 
            "extract": "text", 
            "multiple": True
        },
        "paragraphs": {
            "selector": "p", 
            "extract": "text", 
            "multiple": True
        },
        "links": {
            "selector": "a", 
            "extract": ["text", "href"], 
            "multiple": True
        }
    }
    
    try:
        # URLにアクセスしてデータを抽出
        extracted_data = crawler.extract(url, extractor, schema=schema)
        
        # 抽出したデータを整形
        data = {
            "url": url,
            "title": extracted_data.get("title", ""),
            "meta_description": extracted_data.get("meta_description", ""),
            "headings": [],
            "paragraphs": extracted_data.get("paragraphs", []),
            "links": []
        }
        
        # 見出しを整形
        for h1 in extracted_data.get("h1_headings", []):
            data["headings"].append({"level": 1, "text": h1})
        
        for h2 in extracted_data.get("h2_headings", []):
            data["headings"].append({"level": 2, "text": h2})
        
        for h3 in extracted_data.get("h3_headings", []):
            data["headings"].append({"level": 3, "text": h3})
        
        # リンクを整形
        if "links" in extracted_data:
            for link in extracted_data["links"]:
                if isinstance(link, dict) and "text" in link and "href" in link:
                    data["links"].append({
                        "text": link["text"],
                        "href": link["href"]
                    })
        
        return data
        
    except Exception as e:
        print(f"エラー: Crawl4AIでのスクレイピング中に問題が発生しました: {e}")
        return {}

def scrape_url_with_crawl4ai(url: str) -> Dict[str, Any]:
    """
    URLを判別して適切なスクレイピング関数を呼び出す
    
    Args:
        url: スクレイピングするURL
        
    Returns:
        Dict: 抽出したデータを含む辞書
    """
    if "sokudan.work" in url:
        return scrape_sokudan_with_crawl4ai(url)
    else:
        return scrape_generic_with_crawl4ai(url)

def main():
    """
    メイン関数: コマンドライン引数を解析して処理を実行
    """
    parser = argparse.ArgumentParser(description='Crawl4AIを使ってURLからデータをスクレイピングしてJSON形式で出力します')
    parser.add_argument('url', help='スクレイピングするURL')
    parser.add_argument('-o', '--output', help='出力するJSONファイル名（指定しない場合は標準出力）')
    parser.add_argument('-p', '--pretty', action='store_true', help='整形して出力')
    
    args = parser.parse_args()
    
    # URLをスクレイピング
    result = scrape_url_with_crawl4ai(args.url)
    
    if not result:
        print("スクレイピングに失敗しました。", file=sys.stderr)
        sys.exit(1)
    
    # JSONに変換
    indent = 2 if args.pretty else None
    json_data = json.dumps(result, ensure_ascii=False, indent=indent)
    
    # 結果を出力
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_data)
        print(f"結果を {args.output} に保存しました。")
    else:
        print(json_data)

if __name__ == "__main__":
    main() 