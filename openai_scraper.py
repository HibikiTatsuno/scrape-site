#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sys
import argparse
import urllib3
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# .envファイルから環境変数を読み込む
load_dotenv()

# SSLの警告を無効化
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_api_key() -> str:
    """
    APIキーを環境変数から取得する
    
    Returns:
        str: APIキー
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません")
    return api_key

def fetch_html(url: str) -> str:
    """
    URLからHTMLを取得する
    
    Args:
        url: 取得するURL
        
    Returns:
        str: HTML文字列
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)  # SSLエラーを回避するためにverify=False
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"エラー: リクエスト中に問題が発生しました: {e}")
        return ""

def extract_main_content(html: str) -> str:
    """
    HTMLから主要なコンテンツを抽出する
    
    Args:
        html: HTML文字列
        
    Returns:
        str: 主要なコンテンツのテキスト
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # 不要な要素を削除
    for tag in soup(['script', 'style', 'iframe', 'nav', 'footer']):
        tag.decompose()
    
    # 主要なコンテンツを抽出
    main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find('div', class_='content')
    
    if main_content:
        return main_content.get_text(separator='\n')
    
    # 主要なコンテンツが見つからない場合、全体のテキストを返す
    return soup.get_text(separator='\n')

def parse_with_openai(html_content: str, url: str) -> Dict[str, Any]:
    """
    OpenAI APIを使用してHTMLコンテンツをJSON形式に変換する
    
    Args:
        html_content: HTMLコンテンツの文字列
        url: スクレイピングしたURL
        
    Returns:
        Dict: 変換されたJSONデータ
    """
    # APIキーを取得
    api_key = get_api_key()
    client = OpenAI(api_key=api_key)
    
    # 統一されたスキーマの定義
    schema = {
        "title": "案件のタイトル",
        "description": "案件の説明",
        "payment_method_type": "報酬の支払い方法",
        "weekly_min_working_hour": "週の最小稼働時間（数値）",
        "weekly_max_working_hour": "週の最大稼働時間（数値）",
        "monthly_min_working_hour": "月の最小稼働時間（数値）",
        "monthly_max_working_hour": "月の最大稼働時間（数値）",
        "hourly_min_unit_price": "時給の下限（数値）",
        "hourly_max_unit_price": "時給の上限（数値）",
        "monthly_min_unit_price": "月単価の下限（数値）",
        "monthly_max_unit_price": "月単価の上限（数値）",
        "working_day_type": "稼働日数",
        "working_style_type": "勤務形態（フルリモート、完全出社など）",
        "prefecture": "都道府県",
        "application_default_message": "応募時に必須の質問"
    }
    
    # 抽出指示
    schema_instruction = """
    あなたはWebページから案件情報を抽出するAIです。
    以下のHTMLから案件情報を抽出し、指定されたJSONスキーマに従ってデータを整形してください。
    
    案件ページには以下の情報が含まれている可能性があります：
    - title: 案件のタイトル
    - description: 案件の説明
    - payment_method_type: 報酬の支払い方法（時給、月単価など）
    - weekly_min_working_hour: 週の最小稼働時間（数値のみ）
    - weekly_max_working_hour: 週の最大稼働時間（数値のみ）
    - monthly_min_working_hour: 月の最小稼働時間（数値のみ）
    - monthly_max_working_hour: 月の最大稼働時間（数値のみ）
    - hourly_min_unit_price: 時給の下限（数値のみ）
    - hourly_max_unit_price: 時給の上限（数値のみ）
    - monthly_min_unit_price: 月単価の下限（数値のみ）
    - monthly_max_unit_price: 月単価の上限（数値のみ）
    - working_day_type: 稼働日数
    - working_style_type: 勤務形態（フルリモート、完全出社など）
    - prefecture: 都道府県
    - application_default_message: 応募時に必須の質問
    
    稼働時間や報酬についてはテキストから適切に数値を抽出してください。
    例えば「週3〜5日」という記述があれば、weekly_min_working_hourは3、weekly_max_working_hourは5となります。
    「時給3000円〜5000円」という記述があれば、hourly_min_unit_priceは3000、hourly_max_unit_priceは5000となります。
    
    すべての項目が見つからない場合は、見つかった項目のみを返してください。数値項目は数値型で返し、見つからない場合はnullとしてください。
    """
    
    # HTMLコンテンツが長すぎる場合は短くする
    max_tokens = 16000  # 適切なトークン数に調整
    html_content_short = html_content[:max_tokens] if len(html_content) > max_tokens else html_content
    
    # OpenAI APIへのプロンプト
    messages = [
        {"role": "system", "content": schema_instruction},
        {"role": "user", "content": f"以下のURL: {url}\n\n以下のHTMLからデータを抽出して、JSONスキーマに従って整形してください:\n\n{html_content_short}\n\nJSONスキーマ:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"}
    ]
    
    # APIリクエスト
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",  # 適切なモデルに変更
            messages=messages,
            temperature=0.0,  # 正確な抽出のため低い温度を設定
            response_format={"type": "json_object"}  # JSON形式の応答を要求
        )
        
        # レスポンスからJSONを抽出
        result = json.loads(response.choices[0].message.content)
        
        # URLを追加
        result["url"] = url
        
        return result
        
    except Exception as e:
        print(f"エラー: OpenAI APIでの処理中に問題が発生しました: {e}")
        return {"error": str(e), "url": url}

def scrape_url_with_openai(url: str) -> Dict[str, Any]:
    """
    URLからHTMLを取得し、OpenAI APIを使用して情報を抽出する
    
    Args:
        url: スクレイピングするURL
        
    Returns:
        Dict: 抽出したデータを含む辞書
    """
    # HTMLを取得
    html = fetch_html(url)
    
    if not html:
        print("HTMLの取得に失敗しました。", file=sys.stderr)
        return {}
    
    # HTMLから情報を抽出
    result = parse_with_openai(html, url)
    
    return result

def main():
    """
    メイン関数: コマンドライン引数を解析して処理を実行
    """
    parser = argparse.ArgumentParser(description='OpenAI APIを使ってURLからデータをスクレイピングしてJSON形式で出力します')
    parser.add_argument('url', help='スクレイピングするURL')
    parser.add_argument('-o', '--output', help='出力するJSONファイル名（指定しない場合は標準出力）')
    parser.add_argument('-p', '--pretty', action='store_true', help='整形して出力')
    parser.add_argument('-s', '--save-html', help='HTMLを保存するファイル名')
    
    args = parser.parse_args()
    
    # HTMLを取得して保存（オプション）
    if args.save_html:
        html = fetch_html(args.url)
        if html:
            with open(args.save_html, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"HTMLを {args.save_html} に保存しました。")
        else:
            print("HTMLの取得に失敗しました。", file=sys.stderr)
            sys.exit(1)
    
    # URLをスクレイピング
    result = scrape_url_with_openai(args.url)
    
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