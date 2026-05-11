#!/usr/bin/env python3
"""
持股管理 CLI 工具
用於匯入、匯出、管理持股資料
"""
import argparse
import sys
from pathlib import Path
from database.portfolio_db import PortfolioDB


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
  
  # 查看持股清單
  python portfolio_cli.py list --user USER123
  
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
            print(f"📊 持股清單 ({len(portfolio)} 檔):\n")
            print(f"{'代碼':<12} {'股數':>8} {'成本':>10} {'備註'}")
            print("-" * 50)
            
            for stock in portfolio:
                symbol = stock['symbol']
                shares = stock.get('shares', 0)
                avg_price = stock.get('avg_price', 0)
                note = stock.get('note', '')
                
                print(f"{symbol:<12} {shares:>8.0f} {avg_price:>10.1f} {note}")
            
            # 計算總成本
            total_cost = sum(s.get('shares', 0) * s.get('avg_price', 0) for s in portfolio)
            print("-" * 50)
            print(f"{'總成本':<12} {'':>8} {total_cost:>10,.0f}")
    
    elif args.command == 'clear':
        if not args.confirm:
            print("⚠️  請使用 --confirm 參數確認清空操作")
            return
        
        db.clear_portfolio(args.user)
        print("✅ 已清空所有持股")


if __name__ == "__main__":
    main()
