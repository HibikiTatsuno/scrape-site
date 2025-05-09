#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import argparse
from typing import Dict, Any, Optional
import urllib3

import requests
from bs4 import BeautifulSoup

# SSLの警告を無効化
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_sokudan_job(url: str) -> Dict[str, Any]:
    """
    SOKUDANの案件ページから情報を抽出してJSONに整形する
    
    Args:
        url: スクレイピングするURL
        
    Returns:
        Dict: 抽出したデータを含む辞書
    """
    # URLからHTMLを取得
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)  # SSLエラーを回避するためにverify=Falseを追加
        response.raise_for_status()  # エラーがあれば例外を発生させる
    except requests.exceptions.RequestException as e:
        print(f"エラー: リクエスト中に問題が発生しました: {e}")
        return {}
    
    # HTMLをパース
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 案件データを格納する辞書
    job_data = {
        "title": "",
        "job_type": [],
        "required_hours": "",
        "salary": "",
        "area": "",
        "required_skills": [],
        "details": "",
        "conditions": {},
        "url": url
    }
    
    # タイトルを抽出
    title_elem = soup.find('h1')
    if title_elem:
        job_data["title"] = title_elem.text.strip()
    
    # 職種を抽出 - 更新されたセレクタ
    job_types = soup.find_all('span', class_='inline-block rounded-md')
    if job_types:
        job_data["job_type"] = [job_type.text.strip() for job_type in job_types if job_type.text.strip()]
    
    # 稼働時間、報酬、エリアを抽出 - 更新されたセレクタ
    # 稼働時間
    hours_elem = soup.find(string=lambda t: t and '稼働時間' in t)
    if hours_elem and hours_elem.find_parent():
        hours_value = hours_elem.find_parent().find_next_sibling('p')
        if hours_value:
            job_data["required_hours"] = hours_value.text.strip()
    
    # 報酬
    salary_elem = soup.find(string=lambda t: t and '報酬' in t)
    if salary_elem and salary_elem.find_parent():
        salary_value = salary_elem.find_parent().find_next_sibling('p')
        if salary_value:
            job_data["salary"] = salary_value.text.strip()
    
    # エリア
    area_elem = soup.find(string=lambda t: t and 'エリア' in t)
    if area_elem and area_elem.find_parent():
        area_value = area_elem.find_parent().find_next_sibling('p')
        if area_value:
            job_data["area"] = area_value.text.strip().replace('\n', ' ')
    
    # 必須スキルを抽出 - 更新されたセレクタ
    skills_section = soup.find('p', string=lambda t: t and '必須スキル' in t)
    if skills_section:
        skills = skills_section.find_next_siblings('span')
        job_data["required_skills"] = [skill.text.strip() for skill in skills if skill.text.strip()]
    
    # 案件詳細を抽出 - 更新されたセレクタ
    details_section = soup.find('h2', string=lambda t: t and '案件詳細' in t)
    if details_section:
        details_div = details_section.find_next_sibling('div', class_='whitespace-pre-line')
        if details_div:
            job_data["details"] = details_div.text.strip()
            
            # 案件詳細から条件を抽出 (例: 【必須条件】など)
            details_text = details_div.text
            conditions = {}
            
            if "【必須条件】" in details_text:
                required_start = details_text.find("【必須条件】")
                required_end = details_text.find("【", required_start + 1) if details_text.find("【", required_start + 1) > 0 else len(details_text)
                conditions["required"] = details_text[required_start:required_end].strip()
            
            if "【歓迎条件】" in details_text:
                preferred_start = details_text.find("【歓迎条件】")
                preferred_end = details_text.find("【", preferred_start + 1) if details_text.find("【", preferred_start + 1) > 0 else len(details_text)
                conditions["preferred"] = details_text[preferred_start:preferred_end].strip()
                
            if "【想定報酬】" in details_text:
                salary_start = details_text.find("【想定報酬】")
                salary_end = details_text.find("【", salary_start + 1) if details_text.find("【", salary_start + 1) > 0 else len(details_text)
                conditions["expected_salary"] = details_text[salary_start:salary_end].strip()
            
            if "【勤務条件】" in details_text:
                work_cond_start = details_text.find("【勤務条件】")
                work_cond_end = details_text.find("【", work_cond_start + 1) if details_text.find("【", work_cond_start + 1) > 0 else len(details_text)
                conditions["work_conditions"] = details_text[work_cond_start:work_cond_end].strip()
            
            # 募集背景も抽出
            if "【募集背景】" in details_text:
                background_start = details_text.find("【募集背景】")
                background_end = details_text.find("【", background_start + 1) if details_text.find("【", background_start + 1) > 0 else len(details_text)
                conditions["background"] = details_text[background_start:background_end].strip()
            
            # 業務内容も抽出
            if "【業務内容詳細】" in details_text:
                job_details_start = details_text.find("【業務内容詳細】")
                job_details_end = details_text.find("【", job_details_start + 1) if details_text.find("【", job_details_start + 1) > 0 else len(details_text)
                conditions["job_details"] = details_text[job_details_start:job_details_end].strip()
            
            job_data["conditions"] = conditions
    
    # 特徴も抽出 (フリーランス歓迎、即日勤務OKなど)
    features = []
    feature_spans = soup.find_all('span', class_='inline-block rounded-full')
    if feature_spans:
        features = [span.text.strip() for span in feature_spans if span.text.strip()]
    job_data["features"] = features
    
    # 公開日を抽出
    publish_date_elem = soup.find('p', class_=lambda c: c and 'text-sokudan-date-in-card-grey' in c)
    if publish_date_elem:
        date_text = publish_date_elem.text.strip()
        if "公開日" in date_text:
            job_data["publish_date"] = date_text.replace("公開日 ：", "").strip()
    
    return job_data

def scrape_generic_site(url: str) -> Dict[str, Any]:
    """
    一般的なWebサイトから情報を抽出する
    
    Args:
        url: スクレイピングするURL
        
    Returns:
        Dict: 抽出したデータを含む辞書
    """
    # URLからHTMLを取得
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)  # SSLエラーを回避するためにverify=Falseを追加
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"エラー: リクエスト中に問題が発生しました: {e}")
        return {}
    
    # HTMLをパース
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 基本データを抽出
    data = {
        "url": url,
        "title": "",
        "meta_description": "",
        "headings": [],
        "paragraphs": [],
        "links": []
    }
    
    # タイトルを抽出
    title = soup.find('title')
    if title:
        data["title"] = title.text.strip()
    
    # メタディスクリプションを抽出
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and 'content' in meta_desc.attrs:
        data["meta_description"] = meta_desc['content']
    
    # 見出しを抽出
    for i in range(1, 7):
        headings = soup.find_all(f'h{i}')
        for heading in headings:
            data["headings"].append({
                "level": i,
                "text": heading.text.strip()
            })
    
    # 段落を抽出
    paragraphs = soup.find_all('p')
    data["paragraphs"] = [p.text.strip() for p in paragraphs if p.text.strip()]
    
    # リンクを抽出
    links = soup.find_all('a')
    for link in links:
        if 'href' in link.attrs:
            data["links"].append({
                "text": link.text.strip(),
                "href": link['href']
            })
    
    return data

def scrape_url(url: str) -> Dict[str, Any]:
    """
    URLを判別して適切なスクレイピング関数を呼び出す
    
    Args:
        url: スクレイピングするURL
        
    Returns:
        Dict: 抽出したデータを含む辞書
    """
    if "sokudan.work" in url:
        return scrape_sokudan_job(url)
    else:
        return scrape_generic_site(url)

def main():
    """
    メイン関数: コマンドライン引数を解析して処理を実行
    """
    parser = argparse.ArgumentParser(description='URLからデータをスクレイピングしてJSON形式で出力します')
    parser.add_argument('url', help='スクレイピングするURL')
    parser.add_argument('-o', '--output', help='出力するJSONファイル名（指定しない場合は標準出力）')
    parser.add_argument('-p', '--pretty', action='store_true', help='整形して出力')
    
    args = parser.parse_args()
    
    # URLをスクレイピング
    result = scrape_url(args.url)
    
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