#!/usr/bin/env python3
"""
持股管理 CLI 工具
用於匯入、匯出、管理持股資料
"""
import argparse
import sys
from pathlib import Path
from database.portfolio_db import PortfolioDB
from agents.portfolio_view import SORT_KEYS, format_portfolio_lines


def main():
    parser = argparse.ArgumentParser(
        description='持股管理 CLI 工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例用法:
  # 從 CSV 匯入持股
  python portfolio_cli.py import --user USER123 --file portfolio.csv --format csv
  
  # 從 JSON 匯入持股（清空現有資料）
  python portfolio_cli.py import --user USER123 --file portfolio.json --format json --clear
  
  # 匯出持股到 CSV
  python portfolio_cli.py export --user USER123 --file my_portfolio.csv --format csv
  
  # 查看持股清單（含名稱、成本、參考損益、更新日；可排序）
  python portfolio_cli.py list --user USER123
  python portfolio_cli.py list --user USER123 --sort pnl --desc
  python portfolio_cli.py list --user USER123 --sort shares --desc
  
  # 清空持股
  python portfolio_cli.py clear --user USER123
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='指令')
    
    # ── import 指令 ──────────────────────────────────
    import_parser = subparsers.add_parser('import', help='匯入持股')
    import_parser.add_argument('--user', required=True, help='使用者 ID')
    import_parser.add_argument('--file', required=True, help='檔案路徑')
    import_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='檔案格式')
    import_parser.add_argument('--clear', action='store_true', help='清空現有持股')
    
    # ── export 指令 ──────────────────────────────────
    export_parser = subparsers.add_parser('export', help='匯出持股')
    export_parser.add_argument('--user', required=True, help='使用者 ID')
    export_parser.add_argument('--file', required=True, help='檔案路徑')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='檔案格式')
    
    # ── list 指令 ────────────────────────────────────
    list_parser = subparsers.add_parser('list', help='查看持股清單')
    list_parser.add_argument('--user', required=True, help='使用者 ID')
    list_parser.add_argument(
        '--sort',
        default='symbol',
        choices=sorted(SORT_KEYS),
        help='排序欄位：symbol, name, shares, avg_price, cost, pnl, pnl_pct, updated_at',
    )
    list_parser.add_argument('--desc', action='store_true', help='降序（預設為升序）')
    
    # ── clear 指令 ───────────────────────────────────
    clear_parser = subparsers.add_parser('clear', help='清空持股')
    clear_parser.add_argument('--user', required=True, help='使用者 ID')
    clear_parser.add_argument('--confirm', action='store_true', help='確認清空')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    db = PortfolioDB()
    
    # ── 執行指令 ─────────────────────────────────────
    if args.command == 'import':
        print(f"📥 匯入持股: {args.file}")
        
        if args.format == 'csv':
            result = db.import_from_csv(args.user, args.file, args.clear)
        else:
            result = db.import_from_json(args.user, args.file, args.clear)
        
        print(f"✅ 成功: {result['success']} 檔")
        print(f"❌ 失敗: {result['failed']} 檔")
        
        if result['errors']:
            print(f"\n錯誤訊息:")
            for error in result['errors']:
                print(f"  - {error}")
    
    elif args.command == 'export':
        print(f"📤 匯出持股: {args.file}")
        
        if args.format == 'csv':
            success = db.export_to_csv(args.user, args.file)
        else:
            success = db.export_to_json(args.user, args.file)
        
        if success:
            print(f"✅ 匯出成功: {args.file}")
        else:
            print(f"❌ 匯出失敗")
    
    elif args.command == 'list':
        portfolio = db.get_portfolio(args.user)

        if not portfolio:
            print("📭 目前沒有持股")
        else:
            text = format_portfolio_lines(
                portfolio,
                sort_key=args.sort,
                reverse=args.desc,
                max_stocks=999,
            )
            print(text)
    
    elif args.command == 'clear':
        if not args.confirm:
            print("⚠️  請使用 --confirm 參數確認清空操作")
            return
        
        db.clear_portfolio(args.user)
        print("✅ 已清空所有持股")


if __name__ == "__main__":
    main()
